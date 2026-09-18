%% Script to calibrate parameters using high-rate data

clearvars
close all

diaryname = sprintf('_diary-%s-%s.txt', mfilename, datetime('now', 'Format', 'yyyyMMdd-HHmmss'));
diary(diaryname);

pe    = 'PositiveElectrode';
ne    = 'NegativeElectrode';
co    = 'Coating';
ctrl  = 'Control';
elyte = 'Electrolyte';
sep   = 'Separator';

doplot = true;
debug = true;
hessian = true;
dosave = true;
gradSteps = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7];
hessianSteps = [1e-5, 1e-6, 1e-7, 1e-8, 1e-9];

getTime = @(states) cellfun(@(s) s.time, states);
getE = @(states) cellfun(@(s) s.(ctrl).E, states);
printer = @(s) disp(jsonencode(s, 'PrettyPrint', true));

%% Fetch experimental data

datafilename = fullfile(getHydra0Dir(), 'raw-data', 'TE_1473.mat');
saveddata    = load(datafilename);
dataraw      = saveddata.experiment;

% The last experiment has the highest discharge current.
k = numel(dataraw.time);
expdata = struct('time', dataraw.time{k} * hour, ...
    'U', dataraw.voltage{k}, ...
    'I', abs(mean(dataraw.current{k})));

%% Initial guess using equilibrium calibration data

filename     = fullfile(getHydra0Dir(), 'parameters', 'equilibrium-calibration-parameters.json');
jsonstructEC = parseBattmoJson(filename);

shortnames = {'pe_vsa', 'ne_D', 'pe_D', 'elyte_bg_ne', 'elyte_bg_pe', 'elyte_bg_sep'};
disp('shortnames:');
printer(shortnames);
useRegionBruggemanCoefficients = any(contains(shortnames, 'elyte_bg'));

numTimesteps = 400;
input0 = struct('I', expdata.I, ...
    'totalTime', expdata.time(end), ...
    'numTimesteps', numTimesteps, ...
    'lowRateParams', jsonstructEC, ...
    'useRegionBruggemanCoefficients', useRegionBruggemanCoefficients, ...
    'include_current_collectors', true);
output0 = runHydra(input0, 'clearSimulation', false);

if debug
    % Check how exp and initial guess compare
    figure; hold on; grid on;
    plot(expdata.time/hour, expdata.U, 'k--');
    plot(getTime(output0.states)/hour, getE(output0.states));
    xlabel('time / h')
    ylabel('potential / V')
    title('initial guess')
    drawnow
end

%% Setup optimization

% Evaluate experimental data at simulation times (allow for
% extrapolation since expdata.time(end) is very close to
% output.states{end}.time)
simtimes = getTime(output0.states);
assert(expdata.time(1) <= simtimes(1));
assert(abs(expdata.time(end) - simtimes(end))/expdata.time(end) < 1e-14);

Evals     = interp1(expdata.time, expdata.U, simtimes, 'linear', 'extrap');
statesExp = cell(numel(output0.states), 1);

for k = 1:numel(output0.states)
    statesExp{k}.time     = simtimes(k);
    statesExp{k}.(ctrl).E = Evals(k);
end

if debug
    % Check that the extracted values are the same as the raw values
    figure; hold on; grid on;
    plot(expdata.time/hour, expdata.U, 'k--');
    plot(getTime(statesExp)/hour, getE(statesExp));
    xlabel('Time / h')
    ylabel('Potential / V')
    title('statesExp')
    drawnow
end

simulatorSetup = SimulationSetup(struct('model', output0.model, ...
    'schedule', output0.schedule, ...
    'initstate', output0.initstate, ...
    'NonLinearSolver', output0.nls, ...
    'OutputMinisteps', false));

% Setup parameters to be calibrated
HRC = HighRateCalibration(simulatorSetup, 'shortnames', shortnames);

% Objective function
lsq = @(simsetup, states, varargin) leastSquaresEI(simsetup, states, statesExp, varargin{:});
v = lsq(simulatorSetup, output0.states);
scaling = sum([v{:}]);
objective = @(p, varargin) evalObjectiveBattmo(p, lsq, simulatorSetup, HRC.getParams(), ...
    'objScaling', scaling, varargin{:});

% Compute and classify sensitivities at the initial parameter values.
[~, sensitivityReport] = computeSensitivities(HRC, objective, scaling);
X0 = sensitivityReport.scaledParameters;
initialParams = sensitivityReport.parameterValues;

if debug
    % The least squares function evaluated at the experimental values
    % should be zero
    v = lsq(simulatorSetup, statesExp);
    assert(norm([v{:}]) == 0.0);

    % Compare gradients calculated using adjoints and finite
    % difference approximation
    disp('Gradient comparison at initial parameters:');
    compareAdjointAndFiniteDifferenceGradients(X0, objective, HRC.shortnames, ...
        'PerturbationSize', gradSteps, ...
        'doplot', true);
end

%% Run optimization

v0 = sensitivityReport.objectiveValue;

callbackfunc = @(history, it) callbackplot(history, it, simulatorSetup, ...
    HRC.getParams(), expdata, ...
    'plotEveryIt', 10, ...
    'objScaling', scaling, ...
    'doplot', doplot);

gradTol = 1e-4;
objChangeTol = -inf;
maxit = 500;
[vopt, Xopt, history] = unitBoxBFGS(X0, objective, ...
    'gradTol', gradTol, ...
    'objChangeTol', objChangeTol, ...
    'lineSearchMaxIt', 10, ...
    'maxInitialUpdate', 0.02, ...
    'maximize', false, ...
    'maxit', maxit, ...
    'logPlot', true, ...
    'callbackfunc', callbackfunc, ...
    'plotEvolution', doplot, ...
    'limitedMemory', ~hessian, ...
    'outputHessian', hessian);

setupOpt = updateSetupFromScaledParameters(simulatorSetup, HRC.getParams(), Xopt);

fprintf('obj val=%1.2f (%1.2f), iter=%d\n', vopt, v0, numel(history.val));
reasonStr = getReasonStr(history, ...
    'gradTol', gradTol, ...
    'objChangeTol', objChangeTol, ...
    'maxit', maxit);
disp(reasonStr);

if debug && numel(history.val) >= 2 && ...
        abs(history.val(end) - history.val(end-1)) < objChangeTol

    % Calculate fd and adjoint gradients at final point
    disp('Gradient comparison at optimized parameters:');
    compareAdjointAndFiniteDifferenceGradients(Xopt, objective, HRC.shortnames, ...
        'PerturbationSize', gradSteps);
end

if doplot
    fig = figure('Position', [100, 100, 560, 560]);
    plotParameterEvolution(diaryname, HRC.shortnames(), 'gradTol', gradTol, 'figure', fig);
end

%% Extract parameters

jsonstructHRC = HRC.export(setupOpt);
filename = fullfile(getHydra0Dir(), 'parameters', 'high-rate-calibration-parameters.json');
writeStruct(jsonstructHRC, filename);
printer(jsonstructHRC);

%% Run model with calibrated parameters

inputOpt = struct('I', expdata.I, ...
    'totalTime', expdata.time(end), ...
    'numTimesteps', numTimesteps, ...
    'lowRateParams', jsonstructEC, ...
    'highRateParams', jsonstructHRC, ...
    'useRegionBruggemanCoefficients', useRegionBruggemanCoefficients, ...
    'include_current_collectors', true);
outputOpt = runHydra(inputOpt, 'clearSimulation', false);

%% Quantify differences

vfinal = lsq(simulatorSetup, outputOpt.states);

getExpUinterp = @(t) interp1(expdata.time, expdata.U, t, 'linear', 'extrap');
RMSE = l2error(getTime(outputOpt.states), getE(outputOpt.states), ...
    expdata.time, expdata.U, 'extrap', true);

fprintf('Final least squares values:\n');
fprintf('vopt: %g\n', vopt);
fprintf('Sum of squares: %g\n', sum([vfinal{:}]));
fprintf('RMSE: %g mV\n', RMSE/milli);

if doplot
    % plot differences
    figure; hold on; grid on;
    voltageResidual = getE(outputOpt.states) - getExpUinterp(getTime(outputOpt.states));
    plot(getTime(outputOpt.states), voltageResidual.^2, ...
        'displayname', '|E_{sim} - E_{exp}|^2');
    plot(getTime(outputOpt.states), [vfinal{:}], 'displayname', 'vfinal');
end

%% Plot

if doplot
    colors = lines(2);
    figure('Units', 'inches', 'Position', [0.1, 0.1, 8, 6]);
    hold on;
    plot(expdata.time/hour, expdata.U, 'k--', 'displayname', 'Experiment 2C');
    plot(getTime(output0.states)/hour, getE(output0.states), ...
        'color', colors(1,:), 'displayname', 'Initial guess');
    plot(getTime(outputOpt.states)/hour, getE(outputOpt.states), ...
        'color', colors(2,:), 'displayname', 'Calibrated');
    xlabel('Time  /  h')
    ylabel('E  /  V')
    legend('location', 'sw')
    axis tight
    ylim([3.45, 4.9])
end

%% Check hessian

if hessian

    % history.hess contains the inverse approximate Hessian in scaled coordinates
    invHscaled = full(history.hess{end});
    hessianFdStep = 1e-6; % Selected from the finite-difference comparison.

    Hscaled = calculateBFGSHessian(invHscaled, HRC.shortnames);
    if debug
        [HfdComparison, HfdReport] = calculateFDHessian(Xopt, objective, ...
            HRC.shortnames, hessianSteps);
        compareHessians(Hscaled, HfdComparison, HfdReport, Xopt, HRC.shortnames);
    end
    [HfdScaled, hessianReport] = calculateFDHessian(Xopt, objective, ...
        HRC.shortnames, hessianFdStep);

    % Export these figures with the other run figures below.
    plotHessianEigenvectors(Hscaled, HRC.shortnames, 'BFGS', 'dosave', dosave);
    plotHessianEigenvectors(HfdScaled, HRC.shortnames, 'FD');

end

%% Print

disp('Results HRC');
printer(jsonstructHRC);

% Report tortuosities from the calibrated regional Bruggeman coefficients.

model = outputOpt.model;
tortuosity = @(vf, bman) vf.^(1-bman);
if any(strcmp(HRC.shortnames(), 'elyte_bg_ne'))
    poro = 1 - model.(ne).(co).volumeFraction;
    bg = model.(elyte).regionBruggemanCoefficients.(ne);
    tauNe = tortuosity(poro, bg);
    fprintf('tau ne %g\n', tauNe);
end
if any(strcmp(HRC.shortnames(), 'elyte_bg_pe'))
    poro = 1 - model.(pe).(co).volumeFraction;
    bg = model.(elyte).regionBruggemanCoefficients.(pe);
    tauPe = tortuosity(poro, bg);
    fprintf('tau pe %g\n', tauPe);
end
if any(strcmp(HRC.shortnames(), 'elyte_bg_sep'))
    poro = model.(sep).porosity;
    bg = model.(elyte).regionBruggemanCoefficients.(sep);
    tauSep = tortuosity(poro, bg);
    fprintf('tau sep %g\n', tauSep);
end

effCond = struct(pe, outputOpt.model.(pe).(co).effectiveElectronicConductivity, ...
    ne, outputOpt.model.(ne).(co).effectiveElectronicConductivity);
disp('Effective electronic conductivities:');
printer(effCond);

disp(reasonStr)

% Print initial and final vals, plus sensitivities
finalParams = cellfun(@(p) p.getParameterValue(setupOpt), HRC.getParams());
sensitivitySummary = table(HRC.shortnames(:), initialParams(:), finalParams(:), ...
    sensitivityReport.scaledSensitivity(:), sensitivityReport.initialGroup(:), ...
    'VariableNames', ...
    {'Shortname', 'InitialValue', 'FinalValue', 'scaledSensitivity', 'InitialGroup'});
fprintf('\nInitial sensitivity classification and calibration results:\n');
disp(sensitivitySummary);

% Save the final state of every open figure, including callback and debug plots.
if dosave
    [diaryFolder, diaryBaseName] = fileparts(diaryname);
    figureFolder = fullfile(diaryFolder, diaryBaseName);
    drawnow;
    figureHandles = findall(groot, 'Type', 'figure');
    for figureIndex = 1:numel(figureHandles)
        figureHandle = figureHandles(figureIndex);
        figureBaseName = sprintf('figure-%03d', figureHandle.Number);
        saveFigureSet(figureHandle, fullfile(figureFolder, figureBaseName));
    end
    fprintf('Saved %d figures to %s\n', numel(figureHandles), figureFolder);
end

% Preserve the exact objective setup and parameter scaling for independent forward analysis.
if hessian
    [diaryFolder, diaryBaseName] = fileparts(diaryname);
    resultFolder = fullfile(diaryFolder, diaryBaseName);
    if ~isfolder(resultFolder)
        mkdir(resultFolder);
    end
    hessianFile = fullfile(resultFolder, 'hessian.mat');
    save(hessianFile, 'Hscaled', 'HfdScaled', 'invHscaled', 'hessianReport', ...
        'Xopt', 'vopt', 'scaling', 'HRC', 'simulatorSetup', 'statesExp', 'expdata', ...
        'input0', 'jsonstructHRC', 'diaryname', 'reasonStr', '-v7.3');
    fprintf('Saved Hessians and optimum simulation setup to %s\n', hessianFile);
end

diary off;



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
