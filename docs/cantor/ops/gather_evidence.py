"""Copy public-safe validation records and listening clips without private node keys."""
import json
from pathlib import Path
import tarfile

root = Path('/cantor/validation/yue2')
summary = {'source_commit': '25455ed8a9164e4fced3e31ea5d239f99300890f'}
read = lambda name: json.loads((root / name).read_text())
matrix = read('matrix-release-04/matrix.json')
summary['precision_matrix'] = {'frames': matrix['frames'], 'steps': matrix['ode_steps'], 'keep_loaded': True, 'variants': {}}
for quant, row in matrix['variants'].items():
    summary['precision_matrix']['variants'][quant] = {
        'cold_seconds': row['cold']['pipeline_seconds'], 'warm_seconds_mean': row['warm_pipeline_seconds_mean'],
        'warm_stage_seconds': [[s['seconds'] for s in r['stages']] for r in row['warm']],
        'warm_sampled_peak_mib': max(r['sampled_device_peak_mib'] for r in row['warm']),
        'fixed_semantic_latents': row.get('fixed_semantic_latent_difference'),
        'fixed_semantic_wave': row.get('fixed_semantic_wave_difference'), 'lm_logits': row.get('lm_logits')}
summary['presets'] = {}
for tier, row in read('presets-release-04/presets.json')['presets'].items():
    summary['presets'][tier] = {'quant': row['quant'], 'vae': row['vae'], 'steps': row['steps'],
        'cold_seconds': row['cold']['pipeline_seconds'], 'warm_seconds_mean': row['warm_seconds_mean'],
        'realtime_factor': row['realtime_factor'],
        'warm_stage_seconds': [[s['seconds'] for s in r['stages']] for r in row['warm']],
        'sampled_peak_mib': max(r['sampled_device_peak_mib'] for r in row['warm'])}
summary['step_sweeps'] = {}
for quant in ['Q8_0', 'Q5_K_M']:
    summary['step_sweeps'][quant] = {steps: {'warm_seconds_mean': row['pipeline_seconds_mean'],
        'latent_difference_from_32': row.get('latent_difference_from_32'),
        'wave_difference_from_32': row.get('wave_difference_from_32')}
        for steps, row in read(f'step-release-04-{quant}/step-sweep.json').items()}
summary['acceptance'] = read('acceptance-release-05.json')
summary['publication'] = read('r2-published-release-06.json')
summary['node'] = read('node-release-04/result.json')
summary['optional_eight_step_seconds'] = read('speed8-release-05/presets.json')['presets']['speed']['warm_seconds_mean']
(root / 'release-summary-06.json').write_text(json.dumps(summary, indent=2) + '\n')
excluded = {'config', 'models', 'library', 'www', 'engines', '__pycache__'}
files = []
for path in root.rglob('*'):
    if not path.is_file() or path.is_symlink() or excluded.intersection(path.relative_to(root).parts):
        continue
    if path.suffix in {'.json', '.log', '.exit', '.abc', '.py', '.sh', '.md'}:
        files.append(path)
    elif path.name in {'codes.bin', 'latents.bin', 'semantic.npy', 'latents.npy'}:
        files.append(path)
    elif path.suffix == '.wav' and any(part in {'review-release-04', 'review-speed8-release-05', 'review-speed16-release-06'} for part in path.parts):
        files.append(path)
archive = root / 'evidence-release-06.tar.gz'
with tarfile.open(archive, 'x:gz') as output:
    for path in sorted(files):
        output.add(path, arcname=str(path.relative_to(root)), recursive=False)
print(json.dumps({'archive': str(archive), 'files': len(files), 'bytes': archive.stat().st_size,
                  'private_node_config_and_keys': 'excluded'}), flush=True)
