% Validate the calibrated P2D model and export curves for cross-tool comparison.

clearvars
close all

mrstDebug(0);

am    = 'ActiveMaterial';
itf   = 'Interface';
pe    = 'PositiveElectrode';
ne    = 'NegativeElectrode';
co    = 'Coating';
sd    = 'SolidDiffusion';
ctrl  = 'Control';
elyte = 'Electrolyte';

dosave = true;
figdir = fullfile(getHydra0Dir(), 'figures');

getTime = @(states) cellfun(@(s) s.time, states);
getE = @(states) cellfun(@(s) s.(ctrl).E, states);

%% Fetch experimental data

% Original data
datafilename = fullfile(getHydra0Dir(), 'raw-data', 'TE_1473.mat');
saveddata    = load(datafilename);
dataraw      = saveddata.experiment;

% Calibrated params
[jsonOpt, jsonOptfn] = createOptJson();

% Find capacity
input     = struct('lowRateParams', jsonOpt, ...
                   'include_current_collectors', true);
outputCap = runHydra(input, 'runSimulation', false);
cap       = computeCellCapacity(outputCap.model);

fig14 = figure('Units', 'inches', 'Position', [0.1, 0.1, 8, 6]);
hold on;
colors = lines(numel(dataraw.time));
rates = [0.05, 0.2, 0.5, 1, 2];
numExperiments = numel(dataraw.time);
assert(numExperiments == numel(rates), ...
       'The number of experiments must match the number of expected rates.');
RMSE = nan(size(rates));
hp2d = gobjects(1, numExperiments);
validationCases = cell(numExperiments, 1);
legtxt = cell(1, numel(rates));

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
                   'highRateParams', jsonOpt, ...
                   'useRegionBruggemanCoefficients', true, ...
                   'include_current_collectors', true);

    output = runHydra(input, 'clearSimulation', false);

    simTime = getTime(output.states);
    simVoltage = getE(output.states);
    RMSE(k) = l2error(expdata.time, expdata.U, simTime, simVoltage, 'extrap', true);

    figure(fig14);
    plot(expdata.time/hour * expdata.I, expdata.U, '--', 'color', colors(k,:));
    hp2d(k) = plot(simTime/hour * expdata.I, simVoltage, 'color', colors(k,:));
    xlabel('Capacity  /  Ah')
    ylabel('Voltage  /  V')
    axis tight
    ylim([3.45, 4.9])
    legtxt{k} = sprintf('%1.2gC RMSE=%2.1f mV', rates(k), RMSE(k)/milli);
    drawnow

    % Export the same states used for the validation plot, without another simulation.
    cmax_ne = output.model.(ne).(co).(am).(itf).saturationConcentration;
    cmax_pe = output.model.(pe).(co).(am).(itf).saturationConcentration;

    caseData = struct('case_name', sprintf('Discharge rate %g', rates(k)), ...
                      'current_a', expdata.I, ...
                      'drate', dischargeRate, ...
                      'experimental', struct('time_s', expdata.time(:)', ...
                                             'voltage_v', expdata.U(:)', ...
                                             'capacity_ah', expdata.time(:)' * expdata.I / hour), ...
                      'battmo', struct('time_s', simTime(:)', ...
                                       'voltage_v', simVoltage(:)', ...
                                       'capacity_ah', simTime(:)' * expdata.I / hour), ...
                      'x_elyte_um'              , getSpatialCoordinate(output.model.(elyte).G)/micro, ...
                      'x_ne_um'                 , getSpatialCoordinate(output.model.(ne).(co).G)/micro, ...
                      'x_pe_um'                 , getSpatialCoordinate(output.model.(pe).(co).G)/micro, ...
                      'elyte_c'                 , stackStateVectors(output.states, @(s) s.(elyte).c(:)), ...
                      'elyte_phi'               , stackStateVectors(output.states, @(s) s.(elyte).phi(:)), ...
                      'ne_phi'                  , stackStateVectors(output.states, @(s) s.(ne).(co).phi(:)), ...
                      'pe_phi'                  , stackStateVectors(output.states, @(s) s.(pe).(co).phi(:)), ...
                      'ne_theta'                , stackStateVectors(output.states, @(s) s.(ne).(co).(am).(sd).cSurface(:)) ./ cmax_ne, ...
                      'pe_theta'                , stackStateVectors(output.states, @(s) s.(pe).(co).(am).(sd).cSurface(:)) ./ cmax_pe);
    validationCases{k} = caseData;

    % Plot supporting voltage curves
    figVoltage = figure('Units', 'inches', 'Position', [0.2, 0.2, 8.2, 5.4]);
    hold on; grid on;
    plot(caseData.experimental.capacity_ah, caseData.experimental.voltage_v, 'k--');
    plot(caseData.battmo.capacity_ah, caseData.battmo.voltage_v, 'color', colors(k,:));
    xlabel('Capacity / Ah')
    ylabel('Voltage / V')
    title(sprintf('%s voltage curve (%1.3g A, %1.2gC)', caseData.case_name, caseData.current_a, caseData.drate))
    legend('Location', 'southwest')
    ylim([3.35, 4.95])

    % Plot supporting state dashboards
    figDashboard = figure('Units', 'inches', 'Position', [0.2, 0.2, 14, 8.5]);
    tiledlayout(2, 3, 'TileSpacing', 'compact', 'Padding', 'compact');
    plotStateTile(nexttile, simTime/hour, caseData.x_elyte_um, caseData.elyte_c, 'Electrolyte concentration / mol m^{-3}');
    plotStateTile(nexttile, simTime/hour, caseData.x_elyte_um, caseData.elyte_phi, 'Electrolyte potential / V');
    plotStateTile(nexttile, simTime/hour, caseData.x_ne_um, caseData.ne_phi, 'Negative electrode potential / V');
    plotStateTile(nexttile, simTime/hour, caseData.x_pe_um, caseData.pe_phi, 'Positive electrode potential / V');
    plotStateTile(nexttile, simTime/hour, caseData.x_ne_um, caseData.ne_theta, 'Negative particle surface stoichiometry / -');
    plotStateTile(nexttile, simTime/hour, caseData.x_pe_um, caseData.pe_theta, 'Positive particle surface stoichiometry / -');
    sgtitle(sprintf('%s state variable contour dashboard', caseData.case_name))

    if dosave
        saveFigureSet(figVoltage, fullfile(figdir, sprintf('Case-%g-voltage', k)));
        saveFigureSet(figDashboard, fullfile(figdir, sprintf('Case-%g-state-dashboard', k)));
    end

end

figure(fig14); drawnow;
hp = gobjects(1, 2);
hp(1) = plot(nan, nan, 'k', 'linestyle', '--');
hp(2) = plot(nan, nan, 'k', 'linestyle', '-');
legend(gca(), hp, {'exp', 'P2D'});
ax = axes('position', get(gca(), 'position'), 'visible', 'off');
legend(ax, hp2d, legtxt, 'location', 'sw');

if dosave
    saveFigureSet(fig14, fullfile(figdir, 'figure-14-experimental-voltages-and-p2d-results'));

    parameterFiles = {'parameters/h0b-base.json', ...
                      'parameters/equilibrium-calibration-parameters.json', ...
                      'parameters/high-rate-calibration-parameters.json', ...
                      sprintf('parameters/%s', jsonOptfn)};
    reference = struct('generated_at', char(datetime('now', 'Format', 'yyyy-MM-dd''T''HH:mm:ss')), ...
                       'source', 'scripts/runValidation.m', ...
                       'matlab_release', version('-release'), ...
                       'capacity_ah', cap / hour, ...
                       'parameter_files', {parameterFiles}, ...
                       'cases', {validationCases});
    referenceFilename = fullfile(figdir, 'battmo-validation-reference.json');
    writeStruct(reference, referenceFilename);
    figureCases = cellfun(@(entry) struct('case_name', entry.case_name, ...
                                          'exp_capacity_ah', entry.experimental.time_s * entry.current_a / hour, ...
                                          'experimental_voltage_v', entry.experimental.voltage_v, ...
                                          'sim_capacity_ah', entry.battmo.time_s * entry.current_a / hour, ...
                                          'sim_voltage_v', entry.battmo.voltage_v), validationCases, 'UniformOutput', false);
    writeStruct(struct('cases', {figureCases}), fullfile(figdir, ...
                                                         'figure-14-experimental-voltages-and-p2d-results.json'));
    fprintf('Wrote %s\n', referenceFilename);
end


function plotStateTile(ax, time_h, x_um, values, plotTitle)

    axes(ax);
    imagesc(time_h, x_um, values);
    axis xy
    grid off
    xlabel('Time / h')
    ylabel('x / \mum')
    title(plotTitle)
    colorbar

end

function values = stackStateVectors(states, getter)

    vectors = cellfun(@(s) getter(s), states, 'UniformOutput', false);
    values = horzcat(vectors{:});

end

function x = getSpatialCoordinate(grid)

    x = grid.parentGrid.tPFVgeometry.cells.centroids(grid.mappings.cellmap);
    x = x(:)';

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
