% Validate the calibrated P2D model and export curves for cross-tool comparison.

clearvars
close all

mrstDebug(0);

ctrl = 'Control';
dosave = true;
scriptDirectory = fileparts(mfilename('fullpath'));

getTime = @(states) cellfun(@(s) s.time, states);
getE = @(states) cellfun(@(s) s.(ctrl).E, states);

%% Fetch experimental data

% Original data
datafilename = fullfile(getHydra0Dir(), 'raw-data', 'TE_1473.mat');
saveddata    = load(datafilename);
dataraw      = saveddata.experiment;

% Calibrated params
filename      = fullfile(getHydra0Dir(), 'parameters', 'equilibrium-calibration-parameters.json');
jsonstructEC  = parseBattmoJson(filename);
filename      = fullfile(getHydra0Dir(), 'parameters', 'high-rate-calibration-parameters.json');
jsonstructHRC = parseBattmoJson(filename);

% Find capacity
input     = struct('lowRateParams', jsonstructEC, ...
    'include_current_collectors', true);
outputCap = runHydra(input, 'runSimulation', false);
cap       = computeCellCapacity(outputCap.model);

fig = figure('Units', 'inches', 'Position', [0.1, 0.1, 8, 6]);
hold on;
colors = lines(numel(dataraw.time));
rates = [0.05, 0.2, 0.5, 1, 2];
numExperiments = numel(dataraw.time);
assert(numExperiments == numel(rates), ...
    'The number of experiments must match the number of expected rates.');
RMSE = nan(size(rates));
hp2d = gobjects(1, numExperiments);
validationCases = cell(numExperiments, 1);

for k = 1:numExperiments

    expdata = struct('time', dataraw.time{k} * hour, ...
        'U', dataraw.voltage{k}, ...
        'I', abs(mean(dataraw.current{k})));

    % Convert measured current to C-rate using the calibrated cell capacity.
    dischargeRate = expdata.I / cap * hour;

    assert(abs(dischargeRate - rates(k))/rates(k) < 0.1, ...
        'Discharge rate %g does not match expected rate %g', dischargeRate, rates(k));

    input = struct('DRate', dischargeRate, ...
        'totalTime', expdata.time(end), ...
        'lowRateParams', jsonstructEC, ...
        'highRateParams', jsonstructHRC, ...
        'useRegionBruggemanCoefficients', true, ...
        'include_current_collectors', true);

    output = runHydra(input, 'clearSimulation', false);

    simulationTime = getTime(output.states);
    simulationVoltage = getE(output.states);
    RMSE(k) = l2error(expdata.time, expdata.U, simulationTime, simulationVoltage, 'extrap', true);

    % Export the same states used for the validation plot, without another simulation.
    validationCases{k} = struct('case_name', sprintf('Discharge rate %d', k), ...
        'current_a', expdata.I, ...
        'drate', dischargeRate, ...
        'experimental', struct('time_s', expdata.time(:)', 'voltage_v', expdata.U(:)'), ...
        'battmo', struct('time_s', simulationTime(:)', 'voltage_v', simulationVoltage(:)'));

    figure(fig);
    plot(expdata.time/hour * expdata.I, expdata.U, '--', 'color', colors(k,:));
    hp2d(k) = plot(simulationTime/hour * expdata.I, simulationVoltage, ...
        'color', colors(k,:));
    drawnow

end

xlabel('Capacity  /  Ah')
ylabel('Voltage  /  V')
axis tight
ylim([3.45, 4.9])

hp = gobjects(1, 2);
hp(1) = plot(nan, nan, 'k', 'linestyle', '--');
hp(2) = plot(nan, nan, 'k', 'linestyle', '-');
legend(gca(), hp, {'exp', 'P2D'});

legtxt = cell(1, numel(rates));
for k = 1:numel(rates)
    legtxt{k} = sprintf('%1.2gC RMSE=%2.1f mV', rates(k), RMSE(k)/milli);
end

ax = axes('position', get(gca(), 'position'), 'visible', 'off');
legend(ax, hp2d, legtxt, 'location', 'sw');

if dosave
    exportgraphics(fig, fullfile(scriptDirectory, 'validation.png'), 'resolution', 300);

    parameterFiles = {'parameters/h0b-base.json', ...
        'parameters/equilibrium-calibration-parameters.json', ...
        'parameters/high-rate-calibration-parameters.json'};
    reference = struct('generated_at', char(datetime('now', 'Format', 'yyyy-MM-dd''T''HH:mm:ss')), ...
        'source', 'scripts/runValidation.m', ...
        'matlab_release', version('-release'), ...
        'capacity_ah', cap / hour, ...
        'parameter_files', {parameterFiles}, ...
        'cases', {validationCases});

    outputDirectory = fullfile(getHydra0Dir(), 'figures');
    if ~isfolder(outputDirectory)
        mkdir(outputDirectory);
    end
    referenceFilename = fullfile(outputDirectory, 'battmo-validation-reference.json');
    writeStruct(reference, referenceFilename);
    fprintf('Wrote %s\n', referenceFilename);
end


%{
  Copyright 2021-2026 SINTEF Industry, Sustainable Energy Technology
  and SINTEF Digital, Mathematics & Cybernetics.

  This file is part of The Battery Modeling Toolbox BattMo

  BattMo is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  BattMo is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with BattMo.  If not, see <http://www.gnu.org/licenses/>.
%}
