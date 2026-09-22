%% Script to calibrate parameters under equilibrium assumptions

clearvars
close all

scriptDirectory = fileparts(mfilename('fullpath'));
diaryFilename = sprintf('_diary-%s-%s.txt', mfilename, datestr(now, 'yyyymmdd-HHMMSS'));
diary(fullfile(scriptDirectory, diaryFilename));

mrstDebug(0);

pe   = 'PositiveElectrode';
ne   = 'NegativeElectrode';
ctrl = 'Control';
am   = 'ActiveMaterial';
itf  = 'Interface';
co   = 'Coating';

getTime = @(states) cellfun(@(s) s.time, states);
getE = @(states) cellfun(@(s) s.(ctrl).E, states);
printer = @(s) disp(jsonencode(s, 'PrettyPrint', true));

%% Fetch experimental data

datafilename = fullfile(getHydra0Dir(), 'raw-data', 'TE_1473.mat');
saveddata    = load(datafilename);
dataraw      = saveddata.experiment;

% The first experiment has the lowest discharge current.
expdata = struct('time', dataraw.time{1} * hour        , ...
                 'U'   , dataraw.voltage{1}            , ...
                 'cap' , abs(trapz(dataraw.time{1}*hour, dataraw.current{1})), ...
                 'I'   , abs(mean(dataraw.current{1})));

%% Initial guess simulation

input = struct('I'                         , expdata.I        , ...
               'totalTime'                 , expdata.time(end), ...
               'include_current_collectors', true);
outputInit = runHydra(input, 'clearSimulation', false);

%% Setup and run optimization

[~, caps] = computeCellCapacity(outputInit.model);
ne_area = 5.2*centi*5.2*centi;
geom3d = parseBattmoJson(fullfile(getHydra0Dir(), 'parameters', 'h0b-geometry-3d.json'));
areas = struct(pe, outputInit.jsonstruct.Geometry.faceArea, ...
               ne, ne_area * geom3d.Geometry.nLayers);
np_ratio = caps.(ne) / caps.(pe) * areas.(ne) / areas.(pe);

ecs = EquilibriumCalibrationSetup(outputInit.model, expdata);
ecs = ecs.setupCalibrationCase(1, 'np_ratio', np_ratio);

doipopt = false;

if doipopt
    ipoptOptions = struct('print_level', 5, ...
                          'tol', 1e-5);
    [Xopt, info] = ecs.runIpOpt(ipoptOptions);
    iter = info.iter;
else
    [Xopt, history] = ecs.runUnitBoxBFGS('plotEvolution', false, ...
                                         'useBounds', true);
    iter = numel(history.val);
end

X0 = ecs.X0;
v0 = ecs.objective(X0);
vopt = ecs.objective(Xopt);
[~, fcomp] = ecs.setupfunction();

%% Print

fprintf('\t\tInitial \t Optimized\n');
elde = {'PE', 'NE'};
for e = 1:2
    fprintf('%s\n', elde{e});
    fprintf('theta100\t %1.5f \t %1.5f\n', X0(2*e-1), Xopt(2*e-1));
    fprintf('alpha    \t %1.5f \t %1.5f\n', X0(2*e), Xopt(2*e));
end

fprintf('obj val=%1.2f (%1.2f), iter=%d\n', vopt, v0, iter);

%% Extract parameters

ecs.totalAmountVariableChoice = 'volumeFraction';
jsonstructEC = ecs.exportParameters(Xopt);
filename = fullfile(getHydra0Dir(), 'parameters', 'equilibrium-calibration-parameters.json');
writeStruct(jsonstructEC, filename);
printer(jsonstructEC);

%% Simulation with calibrated parameters

input = struct('I'                         , expdata.I        , ...
               'totalTime'                 , expdata.time(end), ...
               'lowRateParams'             , jsonstructEC     , ...
               'include_current_collectors', true);
outputOpt = runHydra(input, 'clearSimulation', false);
cssOpt = CellSpecificationSummary(outputOpt.model);
fprintf('NP ratio after calibration: %g\n', cssOpt.NPratio);

%% Plot

colors = lines(4);
fig = figure;
hold on
plot(expdata.time/hour, expdata.U, 'k--', 'displayname', 'Experiment 0.05 C');
plot(expdata.time/hour, fcomp(expdata.time, X0), 'color', colors(3,:), 'displayname', 'Initial data');
plot(expdata.time/hour, fcomp(expdata.time, Xopt), 'color', colors(4,:), 'displayname', 'After cell balancing');
plot(getTime(outputOpt.states)/hour, getE(outputOpt.states), 'color', colors(2,:), 'displayname', 'P2D after cell balancing');
xlabel 'Time  /  h';
ylabel 'E  /  V';
legend('location', 'sw')
axis tight
ylim([3.45, 4.9])

RMSE = l2error(expdata.time, expdata.U, getTime(outputOpt.states), getE(outputOpt.states), 'extrap', true);
fprintf('RMSE after calibration: %g mV\n', RMSE/milli);

%% Plot electrode and full-cell OCPs before and after cell balancing

expTime = expdata.time(:);
experimentDuration = expTime(end) - expTime(1);
extendedTime = linspace(expTime(1), expTime(end) + 0.4 * experimentDuration, numel(expTime))';

% Use the same calibration coordinates as the optimization, without new simulations.
[initCellOCP, initpeOCP, initneOCP] = ecs.computeF(extendedTime, X0);
[calibratedCellOCP, calibratedpeOCP] = ecs.computeF(expTime, Xopt);

neInterface = outputInit.jsonstruct.(ne).(co).(am).(itf);
peInterface = outputInit.jsonstruct.(pe).(co).(am).(itf);
neOCPLimit = computeOCPanodeH0b(neInterface.guestStoichiometry0);
peOCPLimit = computeOCPcathodeH0b(peInterface.guestStoichiometry0);

% Retain curves up to the init electrode discharge limits. If a limit is not
% reached in the extended window, retain the available curve instead of an empty slice.
peEndIndex = find(initpeOCP <= peOCPLimit, 1, 'first');
if isempty(peEndIndex)
    peEndIndex = numel(extendedTime);
end
neEndIndex = find(initneOCP >= neOCPLimit, 1, 'first');
if isempty(neEndIndex)
    neEndIndex = numel(extendedTime);
end

% Extend the calibrated graphite curve to ne capacity to show electrode balancing.
neTime = linspace(expTime(1) - 0.4 * experimentDuration, ...
    extendedTime(end), numel(extendedTime))';
[~, ~, calibratedneOCP] = ecs.computeF(neTime, Xopt);
calibratedneEndIndex = find(calibratedneOCP >= neOCPLimit, 1, 'first');
if isempty(calibratedneEndIndex)
    calibratedneEndIndex = numel(neTime);
end
neTime = neTime(1:calibratedneEndIndex);
calibratedneOCP = calibratedneOCP(1:calibratedneEndIndex);
neStartIndex = find(calibratedneOCP >= 0, 1, 'first');
assert(~isempty(neStartIndex), 'No nonne calibrated graphite OCP values to plot.');
neTime = neTime(neStartIndex:end);
calibratedneOCP = calibratedneOCP(neStartIndex:end);

% Convert constant-current charge in A s to mAh per cm^2 of model face area.
faceArea = outputInit.jsonstruct.Geometry.faceArea;
arealCapacity = @(time) expdata.I * (time - expTime(1)) / hour / milli ...
    * centi^2 / faceArea;
expCapacity = arealCapacity(expTime);
initpeCapacity = arealCapacity(extendedTime(1:peEndIndex));
initneCapacity = arealCapacity(extendedTime(1:neEndIndex));
calibratedneCapacity = arealCapacity(neTime);

balancingColors = lines(3);
balancingFigure = figure('Units', 'inches', 'Position', [0.2, 0.2, 7.2, 6.2]);
hold on;
grid on;
plot(initneCapacity, initneOCP(1:neEndIndex), ...
    'DisplayName', 'Graphite init', ...
    'Color', balancingColors(1,:), ...
    'LineStyle', '--');
plot(initpeCapacity, initpeOCP(1:peEndIndex), ...
    'DisplayName', 'LNMO init', ...
    'Color', balancingColors(2,:), ...
    'LineStyle', '--');
plot(initpeCapacity, initCellOCP(1:peEndIndex), ...
    'DisplayName', 'Full Cell init', ...
    'Color', balancingColors(3,:), ...
    'LineStyle', '--');
plot(calibratedneCapacity, calibratedneOCP, ...
    'DisplayName', 'Graphite opt', 'Color', balancingColors(1,:));
plot(expCapacity, calibratedpeOCP, ...
    'DisplayName', 'LNMO opt', 'Color', balancingColors(2,:));
plot(expCapacity, calibratedCellOCP, ...
    'DisplayName', 'Full Cell opt', 'Color', balancingColors(3,:));
plot(expCapacity, expdata.U, 'k:', 'DisplayName', 'Experiment 0.05 C');
xlabel('Capacity / mAh cm^{-2}');
ylabel('Voltage / V');
title('Figure 12. Cell balancing under equilibrium assumption');
legend('Location', 'southwest');
axis tight;
breakyaxis([1.5, 3]);

dosave = true;
if dosave
    figureFilename = 'figure-12-cell-balancing-under-equilibrium-assumption';
    saveFigureSet(balancingFigure, fullfile(getHydra0Dir(), 'figures', figureFilename));
    curveData = @(capacity, voltage) struct('capacity_mAh_cm2', capacity(:)', ...
        'voltage_v', voltage(:)');
    figureData = struct('graphite_init', curveData(initneCapacity, initneOCP(1:neEndIndex)), ...
        'lnmo_init', curveData(initpeCapacity, initpeOCP(1:peEndIndex)), ...
        'full_cell_init', curveData(initpeCapacity, initCellOCP(1:peEndIndex)), ...
        'graphite_opt', curveData(calibratedneCapacity, calibratedneOCP), ...
        'lnmo_opt', curveData(expCapacity, calibratedpeOCP), ...
        'full_cell_opt', curveData(expCapacity, calibratedCellOCP), ...
        'experiment', curveData(expCapacity, expdata.U));
    writeStruct(figureData, fullfile(getHydra0Dir(), 'figures', [figureFilename, '.json']));
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
