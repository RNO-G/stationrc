import json
import logging
import logging.config
import pathlib

from .Executor import Executor


def rootify(data_dir, mattak_dir='', logger=logging.getLogger('root')):
    datadir = pathlib.Path(data_dir)
    
    daqstatus_root = datadir / 'daqstatus.root'
    header_root = datadir / 'header.root'
    waveforms_root = datadir / 'waveforms.root'
    
    proc = Executor(cmd=[pathlib.Path(mattak_dir) / 'rno-g-convert', 'ds', daqstatus_root] + list((datadir / 'daqstatus').glob('*.ds.dat*')), logger=logger)
    proc.wait()
    proc = Executor(cmd=[pathlib.Path(mattak_dir) / 'rno-g-convert', 'hd', header_root] + list((datadir / 'header').glob('*.hd.dat*')), logger=logger)
    proc.wait()
    proc = Executor(cmd=[pathlib.Path(mattak_dir) / 'rno-g-convert', 'wf', waveforms_root] + list((datadir / 'waveforms').glob('*.wf.dat*')), logger=logger)
    proc.wait()
    proc = Executor(cmd=[pathlib.Path(mattak_dir) / 'rno-g-combine', datadir / 'combined.root', waveforms_root, header_root, daqstatus_root], logger=logger)
    proc.wait()


def setup_logging():    
    with open(pathlib.Path(__file__).parent / 'conf/logging_conf.json', 'r') as f:
        conf = json.load(f)
    logging.config.dictConfig(conf)
