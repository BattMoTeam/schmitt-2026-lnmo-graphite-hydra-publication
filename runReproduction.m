% Reproduce publication Figures 12-16 using the calibration and plotting scripts.

cd(fileparts(mfilename('fullpath')));

fprintf('Running full publication reproduction workflow...\n');
fprintf('Stage 1/5: BattMo startup\n');
startup

fprintf('Stage 2/5: Low-rate equilibrium calibration (Figure 12)\n');
run(fullfile('scripts', 'low-rate-calibration', 'runEquilibriumCalibration.m'));

fprintf('Stage 3/5: High-rate calibration (Figures 13 and 16)\n');
run(fullfile('scripts', 'high-rate-calibration', 'runHighRateCalibration.m'));

fprintf('Stage 4/5: Validation (Figure 14)\n');
run(fullfile('scripts', 'runValidation.m'));

fprintf('Stage 5/5: Initial parameter sensitivities (Figure 15)\n');
run(fullfile('scripts', 'high-rate-calibration', 'plotSensitivities.m'));
