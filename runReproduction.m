% Run the full MATLAB-side publication reproduction workflow from the repo root.

cd(fileparts(mfilename('fullpath')));

fprintf('Running full publication reproduction workflow...\n');
fprintf('Stage 1/5: BattMo startup\n');
startup

fprintf('Stage 2/5: Low-rate equilibrium calibration\n');
run(fullfile('scripts', 'low-rate-calibration', 'runEquilibriumCalibration.m'));

fprintf('Stage 3/5: High-rate calibration\n');
run(fullfile('scripts', 'high-rate-calibration', 'runHighRateCalibration.m'));

fprintf('Stage 4/5: Validation and rate-study reference exports\n');
run(fullfile('scripts', 'exportValidationReference.m'));
run(fullfile('scripts', 'exportRateStudyReference.m'));

fprintf('Stage 5/5: Publication figure export\n');
run(fullfile('scripts', 'exportPublicationFigures.m'));

fprintf('\nPrimary publication outputs:\n');
fprintf('  parameters/equilibrium-calibration-parameters.json\n');
fprintf('  parameters/high-rate-calibration-parameters.json\n');
fprintf('  figures/battmo-validation-reference.json\n');
fprintf('  figures/figure-12-cell-balancing-under-equilibrium-assumption.fig\n');
fprintf('  figures/figure-12-cell-balancing-under-equilibrium-assumption.png\n');
fprintf('  figures/figure-13-high-rate-calibration-at-2C.fig\n');
fprintf('  figures/figure-13-high-rate-calibration-at-2C.png\n');
fprintf('  figures/figure-14-experimental-voltages-and-p2d-results.fig\n');
fprintf('  figures/figure-14-experimental-voltages-and-p2d-results.png\n');
fprintf('  figures/supporting/...\n');
fprintf('  figures/publication/INP5-70-120-H0B_graphite-lnmo_schmitt-2026_battmo-vs-experiment-summary.json\n');
fprintf('  figures/publication/INP5-70-120-H0B_graphite-lnmo_schmitt-2026_battmo-vs-experiment.png\n');
fprintf('  figures/rate-study/battmo-rate-study-reference.json\n');
