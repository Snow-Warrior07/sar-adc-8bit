"""Update the existing public profile and portfolio after all project gates pass."""
import json,shutil,subprocess
from pathlib import Path
from tools.common import ROOT,save


def run():
    for number in range(10):
        gate=json.loads((ROOT/f'results/phases/phase-{number:02d}.json').read_text())
        if gate['status']!='passed':raise RuntimeError(f'Phase {number} is not passed; profile integration postponed')
    char=json.loads((ROOT/'results/characterization.json').read_text())
    enob=char['dynamic_low']['enob']
    workspace=ROOT.parent;profile=workspace/'.profile-work'/'Snow-Warrior07';portfolio=workspace/'abhitesh-portfolio'
    config_path=profile/'profile.json';config=json.loads(config_path.read_text(encoding='utf-8'))
    project={'repo':'sar-adc-8bit','title':'8-BIT SAR ADC','category':'MIXED-SIGNAL / RTL',
             'summary':['Differential SAR conversion with a verified RTL controller.',
                        'Online SKY130 circuit tests and a calibrated analog model.',
                        'Static linearity, coherent FFTs and mapped digital timing.'],
             'stack':'SYSTEMVERILOG · PYTHON · NGSPICE · SKY130 · YOSYS',
             'detail':f'8 bits · 100 kS/s model · {enob:.2f} simulated ENOB',
             'url':'https://github.com/Snow-Warrior07/sar-adc-8bit',
             'evidence':'https://github.com/Snow-Warrior07/sar-adc-8bit/blob/main/report/engineering-report.md','latest':True}
    config['projects']=[p for p in config['projects'] if p['repo']!='sar-adc-8bit']+[project]
    config['subtitle']='Mixed-signal Design · Control Systems · Computer Vision'
    config['focus']='SAR conversion · verified RTL · control systems · reproducible experiments'
    config_path.write_text(json.dumps(config,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    script_path=profile/'scripts/update-profile.mjs';script=script_path.read_text(encoding='utf-8')
    replacements={
        'I build at the intersection of intelligent machines and visual data.':'I build circuits, control systems and learning pipelines.',
        'Control loops for autonomous robots. Learning pipelines for large images.':'Verified SAR logic. Online analog simulation. Reproducible experiments.',
        'Robotics · control engineering · computer vision · representation learning':'Mixed-signal design · RTL verification · controls · computer vision',
        'Traction-aware autonomy and efficient high-resolution image pipelines':'SAR conversion, traction-aware autonomy and visual learning',
        "['AUTONOMY', 'traction-aware-amr', 'motion + estimation', 'PI / LQR / nonlinear control', 'ROS 2 + simulation + PCB'],":"['MIXED-SIGNAL', '8-bit SAR ADC', 'charge + decisions', 'SystemVerilog + SKY130', 'online circuits + verification'],",
        "['VISION', 'satellite segmentation', 'pixels + context', 'Residual U-Net + dilations', 'patches + TTA + reconstruction'],":"['AUTONOMY', 'traction-aware-amr', 'motion + estimation', 'PI / LQR / nonlinear control', 'ROS 2 + simulation + PCB'],",
        "['REPRESENTATIONS', 'VAE-Triage', 'compression + quality', 'VQ-VAE + anomaly scoring', 'memory-mapped tiles + ONNX']":"['VISION', 'segmentation + VQ-VAE', 'pixels + representation', 'Residual U-Net + VQ-VAE', 'tiling + learning + inference']",
        'Three project tracks connect robotics, satellite vision, and VQ-VAE representation learning through reproducible experimentation.':'Mixed-signal conversion, robotics and computer vision connect through reproducible experimentation.',
        "'Traction-aware control', 18) + text(48, 284, 'and high-resolution learning.'":"'SAR conversion and verified RTL', 18) + text(48, 284, 'with control systems and learning.'"
    }
    for old,new in replacements.items():script=script.replace(old,new)
    glyph_marker='  const glyph = (index, x, y) => {'
    chip="""\n    if (index === 4) {\n      let pins = '';\n      for (let j = 0; j < 4; j++) pins += line(x - 8, y + 12 + j * 18, x + 8, y + 12 + j * 18, c.fg) + line(x + 80, y + 12 + j * 18, x + 96, y + 12 + j * 18, c.fg);\n      return panel(x + 8, y, 72, 82) + pins + mono(x + 44, y + 38, 'SAR', 13, c.fg, 'text-anchor="middle"') + text(x + 44, y + 60, '8 BIT', 12, c.muted, 'text-anchor="middle"');\n    }"""
    if "if (index === 4)" not in script:script=script.replace(glyph_marker,glyph_marker+chip)
    lines=script.splitlines()
    for i,line in enumerate(lines):
        if '**Latest project:' in line:
            lines[i]="${config.projects.filter(project => project.latest || (!config.projects.some(item => item.latest) && project.demo)).map(project => `**Latest project: [${project.title}](${project.url})** · [Engineering evidence](${project.evidence || project.url})`).join('\\n')}"
    script_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    html_path=portfolio/'dist/index.html';html=html_path.read_text(encoding='utf-8')
    asset=portfolio/'dist/assets/sar-adc-characterization.png';shutil.copy2(ROOT/'report/figures/adc-characterization.png',asset)
    if 'id="adc-details"' not in html:
        card=f'''\n      <article class="featured-project wide" data-category="circuits"><div class="project-copy"><p class="eyebrow">NEW / MIXED-SIGNAL DESIGN</p><h3>8-bit SAR<br>analog-to-digital converter.</h3><p>A differential ADC project connecting verified SystemVerilog control, online SKY130 circuit simulations and a calibrated analog model.</p><div class="project-facts"><span><strong>08</strong> bit resolution</span><span><strong>{enob:.2f}</strong> simulated ENOB</span></div><ul class="tag-list" aria-label="ADC technologies"><li>SystemVerilog</li><li>Python</li><li>ngspice</li><li>SKY130</li><li>Yosys</li></ul><div class="project-actions"><a class="button primary" href="https://github.com/Snow-Warrior07/sar-adc-8bit" target="_blank" rel="noopener noreferrer">Explore ADC design</a><button class="quiet-link detail-trigger" type="button" data-dialog="adc-details" aria-label="Read ADC case study">Case study</button></div></div><div class="project-preview"><div class="preview-caption mono">RTL + ANALOG MODEL / MEASURED SIMULATION</div><img src="assets/sar-adc-characterization.png" width="1920" height="1200" loading="lazy" alt="ADC model transfer curve, static linearity and coherent FFT measurements"><p class="preview-note">Online circuit evidence. Declared model assumptions.</p></div></article>\n'''
        html=html.replace('<div class="projects-grid">','<div class="projects-grid">'+card,1)
        dialog=f'''\n  <dialog class="case-dialog" id="adc-details" aria-labelledby="adc-case-title"><div class="dialog-top"><span class="eyebrow">MIXED-SIGNAL / PROJECT NOTES</span><button type="button" class="dialog-close" aria-label="Close ADC case study">Close <span aria-hidden="true">×</span></button></div><div class="dialog-body"><p class="eyebrow">ANALOG MODELLING &amp; DIGITAL VERIFICATION</p><h2 id="adc-case-title">8-bit differential SAR ADC</h2><p class="case-intro">How do sampled charge, comparator decisions and RTL timing work together to convert an analog signal?</p><img class="case-image" src="assets/sar-adc-characterization.png" alt="Measured static and dynamic ADC model characterization"><h3>The implementation</h3><ul><li>Binary and one-hot synthesizable SAR controllers with real RTL simulation.</li><li>11,021 input conversions, all 256 comparator-decision sequences, reset/recovery and continuous timing checks.</li><li>Online SKY130 comparator and sampled-CDAC circuit characterization, followed by analog-model calibration.</li><li>Two 4,096-sample coherent records, static linearity and capacitor-mismatch sensitivity experiments.</li></ul><h3>What the evidence means</h3><p>The nominal RTL-plus-analog model achieved {enob:.3f} effective bits near 1 kHz at a modelled 100 kS/s. Selected circuits ran in online SPICE; full-system noise and mismatch include declared behavioural assumptions. These are simulation results, with no fabricated chip or full-chip layout claim.</p><div class="project-actions"><a class="button primary" href="https://github.com/Snow-Warrior07/sar-adc-8bit" target="_blank" rel="noopener noreferrer">Read source and tests</a><a class="button secondary" href="https://github.com/Snow-Warrior07/sar-adc-8bit/blob/main/report/engineering-report.md" target="_blank" rel="noopener noreferrer">Engineering report</a></div></div></dialog>\n'''
        html=html.replace('</body>',dialog+'</body>')
    if 'data-filter="circuits"' not in html:
        html=html.replace('<button type="button" data-filter="robotics"', '<button type="button" data-filter="circuits" aria-pressed="false">Circuits &amp; RTL</button><button type="button" data-filter="robotics"',1)
    html=html.replace('04 PROJECTS','05 PROJECTS')
    html=html.replace('ROBOTICS · VISION · DECISION SYSTEMS','MIXED-SIGNAL · ROBOTICS · VISION')
    html=html.replace('My projects connect control engineering, computer vision and optimization.','My projects connect mixed-signal design, control engineering, computer vision and optimization.')
    if '<dt>Digital design</dt>' not in html:
        html=html.replace('<div><dt>Hardware</dt>', '<div><dt>Digital design</dt><dd>SystemVerilog · Yosys · OpenSTA</dd></div><div><dt>Hardware</dt>',1)
    html_path.write_text(html,encoding='utf-8')
    readme=portfolio/'README.md';text=readme.read_text(encoding='utf-8').replace('four featured repositories','five featured repositories')
    if project['url'] not in text:text+='\n- '+project['url']+'\n'
    readme.write_text(text,encoding='utf-8')
    save('results/profile-portfolio-integration.json',{'status':'prepared','profile_projects':len(config['projects']),
        'project_url':project['url'],'portfolio_url':'https://snow-warrior07.github.io/',
        'measured_model_enob':enob,'files':['profile.json','scripts/update-profile.mjs','dist/index.html','dist/assets/sar-adc-characterization.png']})
    print('Profile and portfolio source updated; regenerate profile assets and validate/deploy both repositories next.')


if __name__=='__main__':run()
