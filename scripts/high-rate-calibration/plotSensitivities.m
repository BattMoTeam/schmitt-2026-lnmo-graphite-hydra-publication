%% Plot initial high-rate sensitivities for all nine candidate parameters
% Run startup.m first. This script builds its own objective from the equilibrium
% parameters and highest-current experiment; no high-rate optimization is run.

clearvars
close all

dosave = true;
scriptDirectory = fileparts(mfilename('fullpath'));

shortnames = {'ne_vsa', 'pe_vsa', 'ne_bg', 'pe_bg', 'ne_D', 'pe_D', ...
              'elyte_bg_ne', 'elyte_bg_pe', 'elyte_bg_sep'};
numTimesteps = 400;

%% Build the same initial simulation used for high-rate calibration

repoRoot = getHydra0Dir();
savedData = load(fullfile(repoRoot, 'raw-data', 'TE_1473.mat'));
experiment = savedData.experiment;
experimentIndex = numel(experiment.time);
experimentalTime = experiment.time{experimentIndex} * hour;
experimentalVoltage = experiment.voltage{experimentIndex};
experimentalCurrent = abs(mean(experiment.current{experimentIndex}));

filename = fullfile(repoRoot, 'parameters', 'equilibrium-calibration-parameters.json');
equilibriumParameters = parseBattmoJson(filename);
simulationInput = struct('I', experimentalCurrent, ...
    'totalTime', experimentalTime(end), ...
    'numTimesteps', numTimesteps, ...
    'lowRateParams', equilibriumParameters, ...
    'useRegionBruggemanCoefficients', true, ...
    'include_current_collectors', true);
simulationOutput = runHydra(simulationInput, 'clearSimulation', false);

% Interpolate measurements onto the fixed schedule used by the adjoint objective.
simulationTimes = cellfun(@(state) state.time, simulationOutput.states);
assert(experimentalTime(1) <= simulationTimes(1));
assert(abs(experimentalTime(end) - simulationTimes(end)) / experimentalTime(end) < 1e-14);
experimentalValues = interp1(experimentalTime, experimentalVoltage, simulationTimes, ...
    'linear', 'extrap');
experimentalStates = cell(numel(simulationTimes), 1);
for stepIndex = 1:numel(simulationTimes)
    experimentalStates{stepIndex}.time = simulationTimes(stepIndex);
    experimentalStates{stepIndex}.Control.E = experimentalValues(stepIndex);
end

simulatorSetup = SimulationSetup(struct('model', simulationOutput.model, ...
    'schedule', simulationOutput.schedule, ...
    'initstate', simulationOutput.initstate, ...
    'NonLinearSolver', simulationOutput.nls, ...
    'OutputMinisteps', false));
calibration = HighRateCalibration(simulatorSetup, 'shortnames', shortnames);

leastSquares = @(setup, states, varargin) leastSquaresEI(setup, states, ...
    experimentalStates, varargin{:});
initialObjectiveTerms = leastSquares(simulatorSetup, simulationOutput.states);
objectiveScaling = sum([initialObjectiveTerms{:}]);
assert(isfinite(objectiveScaling) && objectiveScaling > 0, ...
    'The initial objective scaling must be finite and positive.');
objective = @(parameters, varargin) evalObjectiveBattmo(parameters, leastSquares, ...
    simulatorSetup, calibration.getParams(), 'objScaling', objectiveScaling, varargin{:});
[sensitivityTable, sensitivityReport] = computeSensitivities(calibration, ...
    objective, objectiveScaling);

%% Plot scaled, physical, and relative sensitivities in the same parameter order

sensitivityFields = {'scaledSensitivity', 'unscaledSensitivity', 'relativeSensitivity'};
plotTitles = {'Scaled Parameter Sensitivities', 'Unscaled Parameter Sensitivities', ...
              'Relative Parameter Sensitivities'};
axisLabels = {'log10(abs(dJ/dx)), x = scaled parameter', ...
              'log10(abs(dJ/dp)), p = physical parameter', 'log10(abs(p*dJ/dp))'};
figureFilenames = {'scaled-parameter-sensitivities', 'unscaled-parameter-sensitivities', ...
                   'figure-15-relative-parameter-sensitivities'};
for plotIndex = 1:numel(sensitivityFields)
    sensitivityFigure = figure;
    bar(log10(abs(sensitivityTable.(sensitivityFields{plotIndex}))));
    set(gca, 'XTick', 1:height(sensitivityTable), ...
        'XTickLabel', sensitivityTable.Parameter, ...
        'TickLabelInterpreter', 'none', ...
        'XTickLabelRotation', 45);
    ylabel(axisLabels{plotIndex}, 'Interpreter', 'none');
    title(plotTitles{plotIndex});
    if dosave
        saveFigureSet(sensitivityFigure, fullfile(scriptDirectory, figureFilenames{plotIndex}));
    end
end
