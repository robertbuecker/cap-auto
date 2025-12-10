

import configparser
import csv
import hashlib
import os
from time import sleep
from typing import *
import warnings
import numpy as np
import xml.etree.ElementTree as ET
from glob import glob
import pandas as pd # TODO: using pandas for convenience, but should be avoided for lightweight package
from cap_auto.cap_control import CAPInstance


_FOM_DICT = {'Rint': 1,
            'Rurim': 2,
            'Rpim': 3,
            'Sigma': 4,
            'SigmaA': 5,
            'SigmaB': 6,
            'CC 1/2': 7,
            'CC*': 8,
            'deltaCC': 9,
            'Rsym': 11,
            'RshelX': 12}


def write_cap_csv(fn: str, ds: List[dict]):
    """Writes a structure of results in csv.DictWriter format into CrysAlisPro ED result viewer CSV format"""

    from textwrap import dedent
    with open(fn, 'w', newline='') as fh:
        fh.write(dedent(
            f'''\
            VERSION 1
            HEADER INFO: 
            Number of experiments: {len(ds)}
            Number of columns {len(ds[0])}



            '''
                ))
        writer = csv.DictWriter(fh, fieldnames=ds[0].keys())
        writer.writeheader()
        for experiment in ds:
            writer.writerow(experiment)


def parse_cap_csv(fn: str, use_raw_cell: bool, filter_missing: bool = True) -> Tuple[List[dict], np.ndarray, np.ndarray]:
    """Parses a CSV experiment report file from the CrysAlisPro ED result viewer for cell parameters"""

    with open(fn) as fh:
        for _ in range(7):
            _ = fh.readline()
        ds = list(csv.DictReader(fh))
        
    key = 'Current unit cell' if use_raw_cell else 'Final SG unit cell'
    ds = [d for d in ds if d[key]] if filter_missing else ds # filter experiments with empty cell parameters (not indexed)
    cells = np.array([d[key].split() for d in ds]).astype(float)
    
    def get_centring(d) -> str:
        if use_raw_cell:
            ctr = d['Current lattice'].strip()[-1]
        else:
            ctr = d['Space group RED'].strip()[0]
        if ctr not in ['P', 'I', 'F', 'A', 'B', 'C', 'R', 'H']:
            warnings.warn(RuntimeWarning(f'Unknown centring {ctr}. Assuming P'))
            ctr = 'P'
        return ctr
    
    centrings = np.array([get_centring(d) for d in ds])

    return ds, cells, centrings


def parse_cap_meta(experiments: Union[str, List[str]], 
                   log_fun: Optional[Callable[[str], None]] = None,
                   include_merged: bool = False,
                   exclude: List[str] = ('tomo', 'DD_Calib', 'Preset', 'Cluster'),
                   include: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    
    # TODO: add more comprehensive metadata extraction as needed
    # TODO: think about making this a class CapExperimentMeta with methods for different metadata extraction... but maybe that's overengineering
    
    if isinstance(experiments, str):
        experiments = [experiments]
    
    log = print if log_fun is None else log_fun
    
    # Step 1: get full path names of all experiments in a robust and consistent way
    exp_list = []
    for exp_entry in experiments:

        if not os.path.exists(exp_entry):
            raise FileNotFoundError(f'Input folder or CSV file {exp_entry} does not exist')

        log(f'Scanning {exp_entry}...')
        if exp_entry.endswith('.csv'):
            with open(exp_entry) as fh:
                for _ in range(7):
                    _ = fh.readline()
                ds = list(csv.DictReader(fh))
                new_exp = [os.path.join(d['Dataset path'], d['Experiment name']) for d in ds]
                log(f'Found {len(new_exp)} experiments in {exp_entry}')

        else:            
            new_exp = [os.path.splitext(fn)[0] for fn in glob(os.path.join(exp_entry,'**\\*.par'), recursive=True) if ('_cracker' not in fn)]
            log(f'Found {len(new_exp)} .par files in {exp_entry}')
            
        exp_list.extend(new_exp)
        
    N = len(exp_list)
    exp_list = [fn for fn in exp_list if all([(expr not in fn) for expr in exclude])]
    log(f'{N-len(exp_list)} experiments were excluded by the exclude list {exclude}')
    
    N = len(exp_list)
    if include is not None:
        exp_list = [fn for fn in exp_list if any([(expr in fn) for expr in include])]
        log(f'{N-len(exp_list)} experiments were excluded by the include list {include}')

    exp_list = sorted(list(set(exp_list)))
    log(f'Found {len(exp_list)} experiments of correct type')
    
    # Step 2: iterate through all experiments and collate metadata from various files
    info = []
    
    for ii, exp in enumerate(exp_list):
        
        # STEP 2.1: XML info file
        info_fn = os.path.join(os.path.dirname(exp), 'experiment_results.xmlinfo')
        if not os.path.exists(info_fn):
            log(f'WARNING: {info_fn} is missing. Skipping this experiment.')
            continue
        
        info_xml_str = open(info_fn).read()
        tree = ET.fromstring('<root>\n' + info_xml_str + '\n</root>')
        exp_info = {'path': exp}
        
        if (exp_type := tree.find('__EXPERIMENT_INFO__/__EXPERIMENT_TYPE__')) is not None:
            if (float(exp_type.text) == 6.) and not include_merged:
                log(f'Skipping merged experiment {exp} (type 6)')
                continue
        
        # generate hash digest stable information (not changing with reprocessing or moving)
        if (user := tree.find('__EXPERIMENT_INFO__/__USER__')) is not None:
            user = user.text
        else:
            user = 'anonymous'
            
        if (exp_time := tree.find('__EXPERIMENT_INFO__/__START_TIME__')) is not None:
            exp_time = exp_time.text
        else:
            exp_time = 'unknown time'
            
        if (exp_name := tree.find('__EXPERIMENT_INFO__/__EXPERIMENT_PAR_NAME_WOEXT__')) is not None:
            exp_name = exp_name.text
        else:
            exp_name = os.path.basename(exp)
        
        exp_info['name'] = exp_name
        
        xml_entries = {
            'scan_range': tree.find('__EXPERIMENT_INFO__/__SCAN_RANGE__'),
            'detector_distance': tree.find('__EXPERIMENT_INFO__/__DETECTOR_DISTANCE__'),
            'indexation': tree.find('__EXPERIMENT_RESULTS__/__INDEXATION__'),
            'e1': tree.find('__EXPERIMENT_RESULTS__/__MOSAICITY__/__MOSAICITY_E1__'),
            'e2': tree.find('__EXPERIMENT_RESULTS__/__MOSAICITY__/__MOSAICITY_E2__'),
            'e3': tree.find('__EXPERIMENT_RESULTS__/__MOSAICITY__/__MOSAICITY_E3__'),
            'diff_limit': tree.find('__EXPERIMENT_RESULTS__/__DIFFLIMIT__'),
            'r_int': tree.find('__EXPERIMENT_RESULTS__/__RINT__'),
            'stage_x': tree.find('__EXPERIMENT_INFO__/__STAGE_POSITION__/__STAGE_POSITION_X__'),
            'stage_y': tree.find('__EXPERIMENT_INFO__/__STAGE_POSITION__/__STAGE_POSITION_Y__'),
            'stage_z': tree.find('__EXPERIMENT_INFO__/__STAGE_POSITION__/__STAGE_POSITION_Z__')
        }
        
        for k, v in xml_entries.items():
            if v is not None:
                exp_info[k] = float(v.text)
        
        m = hashlib.md5()
        hash_text = ';'.join([user, exp_time, exp_name])
        m.update(hash_text.encode()) # this line defines what gets hashed
        exp_info['digest'] = m.hexdigest()
                
        # STEP 2.2: queue info file
        xpos, ypos = 387.5, 192.5
        if os.path.exists(qedfile := os.path.join(os.path.dirname(exp), 'metadataexpsettings.qed')):
            with open(qedfile, 'r') as fh:
                for ln in fh:
                    if ln.startswith('s_experimentsettings_metadata.s_queue_singletask.ssampleinfo_template.srequestedposition.la_abspixelrequestedposition_xy2[0]'):
                        xpos = int(ln.split('=')[1].strip())
                    if ln.startswith('s_experimentsettings_metadata.s_queue_singletask.ssampleinfo_template.srequestedposition.la_abspixelrequestedposition_xy2[1]'):
                        ypos = int(ln.split('=')[1].strip())

        exp_info['grain_x_px'] = xpos
        exp_info['grain_y_px'] = ypos
        
        # STEP 2.3: data collection ini file
        try:
            config = configparser.ConfigParser()
            config.read(os.path.join(os.path.dirname(exp), 'expinfo', exp_name + '_datacoll.ini'))
            OL_demag, visual_pxs = 47, 0.036
            try:
                exp_info['aperture_px'] = float(config['MicroED'].get('Aperture SA info', None)) / OL_demag / visual_pxs
            except (KeyError, ValueError):
                exp_info['aperture_px'] = -1  # -1 means aperture size could not be decoded
        except Exception as err:
            log('Could not decode aperture size for', exp)
            
        # STEP 2.4: check grain images and diffraction images
        extensions = ['rodhypix', 'jpg', 'tiff']
        kinds = {'diff': 'middle_microed_diff_snapshot',
                 'grain': 'microed_grain_snapshot',
                 'minimap': 'microed_minimap_snapshot',
                 'post': 'microed_post_snapshot'}
        
        #TODO minimap JPG needs special treatment, as it has coordinates in filename
        for kind, fn_label in kinds.items():
            for ext in extensions:
                fn = os.path.join(os.path.dirname(exp), exp_name + '_' + fn_label + '.' + ext)
                if os.path.exists(fn):
                    exp_info[kind + '-' + ext] = fn
                    
        info.append(exp_info)
        
        #TODO: add more metadata extraction as needed
        #TODO: add error handling for missing or malformed files
        #TODO: create a summary CSV file if desired with all metadata
        
    return info

class ProffitXML:
    #TODO implement a class for proffit XML files, analogous to FinalizationXML (after this is, well... finalized)
    pass

def get_diff_info(path, cap: Optional[CAPInstance] = None,
                  keep_peak_file: bool = False, keep_powder_file: bool = False,
                  redo_peak_hunt: bool = True, wavelength: float = 0.0251, pow_dmin: float = 0.3, pow_dmax: float = 20,
                  recenter_pattern: bool = True,
                  log: Optional[Callable] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    """Reads reduced diffraction information from a CAP experiment: peak table and/or powder pattern. Generates them if not already present.
    Peak data as written by WD OLDASCIIT, powder data as written by POWDER RADIAL.
    """

    # TODO: this function is a total mess, needs refactoring to avoid pandas and improve structure. Probably best to make it a class DiffInfo with file parsing in get functions (with consistent set of file names) and recomputation methods.
    # TODO: most urgently, separate file creation in CAP, data parsing, and shell data computation, possibly even into different classes.
    # TODO: creating the files via CAPInstance should be optional (or using CAP at all), the way this is handled is confusing

    if log is None:
        log = print

    if cap is None:
        #TODO this is the old-style CAPInstance, needs to be updated to cap_auto
        cap = CAPInstance(par_file=path + '.par', cap_folder='C:\\Xcalibur\\CrysAlisPro171.45')
    else:
        cap.load_experiment(path + '.par')

    need_center = False
    cmds = []

    # Powder data extraction
    powder_fn = os.path.join(os.path.dirname(path), 'radial.dat')
    
    if (have_file := os.path.exists(powder_fn)) and keep_powder_file:        
        log(f"Keeping existing powder file: {powder_fn}")        
            
    else:
        if have_file:
            log(f"Removing existing powder file: {powder_fn}")
            os.remove(powder_fn)
        cmds.append(f'powder radial 128 {wavelength/pow_dmax*180/np.pi} {wavelength/pow_dmin*180/np.pi} 0 360 radial')
        need_center = True

    peak_fn = path + '.tab'
    
    if (have_file := os.path.exists(peak_fn)) and keep_peak_file:
        log(f"Keeping existing peak file: {peak_fn}")
            
    else:
        if have_file:
            log(f"Removing existing peak file: {peak_fn}")
            os.remove(peak_fn)
        if redo_peak_hunt:
            log(f"Will re-run peak hunt and write result into: {peak_fn}")
            cmds.append(f'ph snogui_pars 1000 20 1 0 2 2 10 10 1 0 0 0 0.0 1000.0 0 1 1 1')
            need_center = True
        else:
            log(f"Will write existing peaks into: {peak_fn}")
            
        cmds.append('wd oldasciit ' + '\"' + path + '\"')

    diff_img_fn = path + '_diff_screen.png'
    try:
        frame_list = glob(os.path.join(os.path.dirname(path), 'frames', '*.rodhypix'))
        
        if len(frame_list) == 1:
            log(f"Only one frame found, using it directly.")            
                        
        else:            
            frame_list.sort(key=lambda fn: int(os.path.splitext(fn)[0].rsplit('_')[-1]))      
            middle_frame = frame_list[len(frame_list) // 2]        
            log(f"Using middle frame for diff image: {os.path.split(middle_frame)[-1]}")
            cmds.append(f'rd i "{middle_frame}"')
        
    except Exception as e:
        log(f"Error finding middle frame for {os.path.basename(path)}: {e}")
        
    cmds.append(f'wd pnggiftiff "{diff_img_fn}"')

    if need_center and recenter_pattern:
        cmds = ['dc microedadjustcenter'] + cmds

    log(f"Running commands for {path}: \n-----\n{'\n'.join(cmds)}\n-----")
    cap.run_cmd(cmds, use_mac=True)

    try:
        ii = 0
        while not os.path.exists(powder_fn):
            sleep(0.1)
            ii += 1
            if ii > 20:
                raise FileNotFoundError(f"Powder result file {powder_fn} not found after 10 seconds.")        
        #
        # TODO: refactor to avoid pandas here. Need to think of a good data structure... maybe a list of namedtuples or dataclass instances?
        powder = pd.read_csv(powder_fn, skiprows=1, sep='\\s+')
        powder['1/d'] = 1/powder['d-value']
        d_min, d_max = powder['d-value'].min(), powder['d-value'].max()
        # TODO: the shell boundaries here are somewhat sensible but should be configurable
        shells = [1/d_max, 1/10, 1/1.2, 1/0.8, 1/(d_min*1.5), 1/d_min]
        powder['shell'] = np.digitize(powder['1/d'], shells, right=False) - 1

    except Exception as e:
        log(f"Error parsing powder data for {path}: {e}")
        raise e

    try:
        ii = 0
        while not os.path.exists(peak_fn):
            sleep(0.1)
            ii += 1
            if ii > 20:
                raise FileNotFoundError(f"Peak hunt result file {peak_fn} not found after 10 seconds.")

        # TODO: refactor to avoid pandas here. Need to think of a good data structure... maybe a list of namedtuples or dataclass instances?
        pk_cols=['x', 'y', 'z', 'R', 'I', 'f', 's', 'm', 'st',
            'centroidx', 'centroidy', 'os', 'ts', 'ks', 'ps', 'op',
            'tp', 'calcstatus', 'runframenumber']
        peak_table = pd.read_csv(peak_fn, sep='\\s+', skiprows=1, header=None).iloc[:,:len(pk_cols)]
        peak_table.columns = pk_cols
        peak_table.dropna(inplace=True)
        peak_table.drop(['os', 'ts', 'f', 's', 'm', 'ks', 'ps', 'op', 'tp', 'st'], axis=1, inplace=True)

        peak_table['1/d'] = peak_table['R']/wavelength
        peak_table['d'] = 1/peak_table['1/d']
        # TODO the shell assignment is too early here, better do it during per-shell data extraction
        peak_table['shell'] = np.digitize(peak_table['1/d'], shells, right=False) - 1

    except Exception as e:
        log(f"Error processing peak data for {path}: {e}")
        raise e

    # get per-shell data from powder data and peak table
    shelldata = []
    # TODO: refactor to avoid pandas here. Should probably go into a separate function anyway. Typical use case for powder and peak_table, so a good test case for an efficient/elegant data structure for those.
    for ii, d_inv in enumerate(shells[:-1]):
        shelldata.append({
            'd_max': 1/d_inv,
            'd_min': 1/shells[ii+1],
            'I_tot': powder[powder['shell'] == ii]['intx'].sum(),
            'I_peak': peak_table[peak_table['shell'] == ii]['I'].sum(),
            'N_peaks': len(peak_table[peak_table['shell'] == ii]),
            'peak_ratio': (peak_table[peak_table['shell'] == ii]['I'].sum() /
                        powder[powder['shell'] == ii]['intx'].sum()
                        if powder[powder['shell'] == ii]['intx'].sum() > 0 else np.nan)
        })

    shelldata = pd.DataFrame(shelldata)

    return shelldata, peak_table, powder, diff_img_fn

   
class FinalizationXML:
        
    def __init__(self, filename: str, path: str, allow_missing: bool = False, parse: bool = True):
        """Open a CAP finalization XML file as generated by `DC RRP` or `DC XMLRRP`

        Args:
            filename (str): XML finalization file generated by CAP
            path (str): Name of finalization (including full experiment path, without extension)
            allow_missing (bool, optional): Allows to create an instance without an actual file. Defaults to False.
            parse (bool, optional): Parse the XML file straight away. Otherwise, it can be done later using `FinalizationXML.update`. 
            Defaults to True.
        """        

        self.filename = filename
        self.path = path
        self.tree = None
        if parse:
            self.update(allow_missing)        
            
    def update(self, allow_missing: bool = False):
        """Updates CAP finalization settings from the XML file

        Args:
            allow_missing (bool, optional): If True and the file is missing, set the internal tree to None instead of
            raising an error. Defaults to False.

        Raises:
            FileNotFoundError: _description_
        """
          
        try:
            self.tree = ET.parse(self.filename)      
        except FileNotFoundError as err:
            if allow_missing:
                self.tree = None
            else:
                raise FileNotFoundError(f'Finalization parameter file {self.filename} does not exist (yet).')
        
    def set_parameters(self, template: Optional[str] = None, 
                    gral: Optional[bool] = None, gral_interactive: Optional[bool] = None,
                    autochem: Optional[bool] = None,
                    laue: Optional[Union[int]] = None, z: Optional[float] = None,
                    chem: Optional[str] = None, res_limit: Optional[float] = None,
                    fom: Union[list, tuple] = ('Rint', 'Rurim', 'Rpim', 'CC 1/2', 'deltaCC', 'Sigma', 'SigmaA', 'SigmaB', 'CC*'),
                    N_shells: int = 10,
                    pars: Optional[Dict[str, str]] = None):
        # TODO would it be more elegant to have a different template mechanism, e.g. during initialization or using a class method?
        # TODO: add more parameters as needed, e.g. with regards to output options, scaling options, etc.
        # TODO: investigate required parameters/procedures for merged data sets in CAP 45
        # TODO: investigte refinalization with consistent GRAL in CAP 45
        
        if template is not None:
            if os.path.exists(template):
                tree = ET.parse(template)
            else:
                raise FileNotFoundError(f'Finalization parameter template file {template} does not exist (yet).')
        elif self.tree is not None:
            tree = self.tree
        else:
            raise ValueError('No finalization parameters are loaded; please specify a template.')
            
        root = tree.getroot()
        root.find('__FINALIZER_SAMPLE__/__Input_file__').text = os.path.basename(self.path)
        root.find('__FINALIZER_SAMPLE__/__Input_file_path__').text = os.path.dirname(self.path)
        root.find('__FINALIZER_OUTPUT__/__Output_file__').text = os.path.basename(self.path)
        root.find('__FINALIZER_OUTPUT__/__Output_file_path__').text = self.path

        pars = {} if pars is None else pars
        
        if gral is not None:
            pars['__FINALIZER_SPACE_GROUP_AND_AUTOCHEM__/__Is_GRAL_on__'] = '1' if gral else '0'
        if gral_interactive is not None:
            pars['__FINALIZER_SPACE_GROUP_AND_AUTOCHEM__/__GRAL_mode__'] = '1' if gral_interactive else '0'            
        if autochem is not None:
            pars['__FINALIZER_SPACE_GROUP_AND_AUTOCHEM__/__Is_AutoChem_active__'] = '1' if autochem else '0'
        if autochem is not None:
            pars['__FINALIZER_SPACE_GROUP_AND_AUTOCHEM__/__Is_AutoChem_active__'] = '1' if autochem else '0'
        if laue is not None:
            if isinstance(laue, str):
                lcls = root.find('__FINALIZER_SAMPLE__/__Type_of_Laue__indexinfo__').text.split(';')
                laue = {v.strip(): int(k) for k, v in (lcl.split('-', 1) for lcl in lcls)}[laue]
            pars['__FINALIZER_SAMPLE__/__Type_of_Laue__'] = str(laue)
        if res_limit is not None:
            pars['__FINALIZER_FILTERS_AND_LIMITS__/__Automated__'] = '0'
            pars['__FINALIZER_FILTERS_AND_LIMITS__/__Apply_resolution_limits__'] = '1'
            pars['__FINALIZER_FILTERS_AND_LIMITS__/__Resolution_limits_-_high_limit__'] = str(res_limit)
            pars['__FINALIZER_FILTERS_AND_LIMITS__/__Dmin_for_completness__'] = str(res_limit)
        if z is not None:
            pars['__FINALIZER_SAMPLE__/__Z__'] = str(z)
        if chem is not None:
            pars['__FINALIZER_SAMPLE__/__Chemical_formula__'] = str(chem)
            
        pars['__FINALIZER_FILTERS_AND_LIMITS__/__Apply_printout_options__'] = '1'
        pars['__FINALIZER_FILTERS_AND_LIMITS__/__Printout_options_-_number_of_shells__'] = str(N_shells)
        
        for ii, the_fom in enumerate(fom):
            # print(the_fom)
            pars[f'__FINALIZER_FILTERS_AND_LIMITS__/__Printout_options_-_Output_order_-_{ii}__'] = str(_FOM_DICT.get(the_fom, 0))
        
        # global settings
        for k, v in pars.items():
            try:
                root.find(k).text = v
            except AttributeError:
                print('Entry', k, 'not found in XML template.')
            
        self.tree = tree        
        
        if self.filename is not None:
            tree.write(self.filename)                   
        else:
            warnings.warn('No parameter XML file name set. Not writing changed parameters', RuntimeWarning)