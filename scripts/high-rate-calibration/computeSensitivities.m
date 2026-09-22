function [senstbl, report] = computeSensitivities(HRC, objective, objectiveScaling, varargin)
% Report derivatives of the unnormalized objective in scaled and physical coordinates.
% Relative sensitivities p*dJ/dp compare equal fractional parameter changes.
% Classification uses scaled coordinates, so it depends on the calibration bounds.
% The table is sorted by absolute scaled sensitivity; the optional report retains HRC parameter order.

    opt = struct('heading', 'Parameter sensitivities');
    opt = merge_options(opt, varargin{:});

    assert(isa(objective, 'function_handle'), ...
           'objective must be a function handle.');
    assert(isscalar(objectiveScaling) && isfinite(objectiveScaling), ...
           'objectiveScaling must be a finite scalar.');

    parameters = HRC.params;
    shortnames = reshape(HRC.shortnames, [], 1);
    scaledParameters = getScaledParameterVector(HRC.simulatorSetup, parameters);
    [objectiveValue, scaledGradient] = objective(scaledParameters);
    % Scaled sensitivity is dJ/dx for the scaled parameter x and unnormalized objective J.
    scaledSensitivity = reshape(scaledGradient .* objectiveScaling, [], 1);

    assert(numel(shortnames) == numel(scaledSensitivity), ...
           'Expected one sensitivity for each parameter shortname.');
    assert(all(isfinite(scaledSensitivity)), ...
           'All scaled parameter sensitivities must be finite.');

    assert(numel(parameters) == numel(scaledSensitivity) && ...
           numel(scaledParameters) == numel(scaledSensitivity), ...
           'Expected one scalar parameter definition for each sensitivity.');
    parameterValues = zeros(size(scaledSensitivity));
    parameterScaleDerivatives = zeros(size(scaledSensitivity));
    for index = 1:numel(parameters)
        parameter = parameters{index};
        assert(parameter.nParam == 1, 'Sensitivity reporting requires scalar parameters.');
        parameterValues(index) = parameter.unscale(scaledParameters(index));
        % scaleGradient(1, p) gives dp/dx for the actual parameter transformation.
        parameterScaleDerivatives(index) = parameter.scaleGradient(1, parameterValues(index));
    end
    assert(all(isfinite(parameterValues)) && ...
           all(isfinite(parameterScaleDerivatives) & parameterScaleDerivatives ~= 0), ...
           'Parameter values and scaling derivatives must be finite and scaling invertible.');

    % Unscaled sensitivity is dJ/dp for the physical parameter p in its original units.
    unscaledSensitivity = scaledSensitivity ./ parameterScaleDerivatives;

    % Relative sensitivity is p*dJ/dp, so a 1% parameter increase changes J by about 0.01 times it.
    relativeSensitivity = parameterValues .* unscaledSensitivity;

    initialGroup = ClassifyScaledSensitivity(scaledSensitivity);

    senstbl = table(shortnames, parameterValues, scaledSensitivity, ...
        unscaledSensitivity, relativeSensitivity, initialGroup, ...
        'VariableNames', {'Parameter', 'Value', 'scaledSensitivity', ...
                          'unscaledSensitivity', 'relativeSensitivity', 'Initial Group'});
    [~, sortIndex] = sort(abs(scaledSensitivity), 'descend');
    senstbl = senstbl(sortIndex, :);

    fprintf('\n=== %s ===\n', opt.heading);
    fprintf('  All sensitivities refer to the unnormalized objective J.\n');
    fprintf('  scaledSensitivity is dJ/dx, the derivative with respect to the scaled parameter x.\n');
    fprintf('  unscaledSensitivity is dJ/dp, the derivative with respect to the physical parameter p.\n');
    fprintf(['  relativeSensitivity is p*dJ/dp; a 1%% parameter increase changes J by ', ...
             'approximately 0.01 times this value.\n']);
    fprintf('  Sorting and classification use the magnitude of scaledSensitivity.\n');
    disp(senstbl);

    report = struct('shortnames', {shortnames}, ...
        'scaledParameters', scaledParameters, ...
        'objectiveValue', objectiveValue, ...
        'scaledGradient', scaledGradient, ...
        'scaledSensitivity', scaledSensitivity, ...
        'parameterValues', parameterValues, ...
        'unscaledSensitivity', unscaledSensitivity, ...
        'relativeSensitivity', relativeSensitivity, ...
        'initialGroup', {initialGroup});

end


function initialGroup = ClassifyScaledSensitivity(scaledSensitivity)
% Group derivative magnitudes using percentiles, with log spacing for wide ranges.

    % Classification depends on derivative magnitudes, independent of their signs.
    scaledSensitivity = abs(scaledSensitivity);
    initialGroup = repmat({''}, numel(scaledSensitivity), 1);

    if all(scaledSensitivity == 0)
        initialGroup(:) = {'Low_Sensitivity'};
        return
    end

    maxScaledSensitivity = max(scaledSensitivity);
    minScaledSensitivity = min(scaledSensitivity);
    scaledSensitivityRatio = maxScaledSensitivity / (minScaledSensitivity + eps);

    if scaledSensitivityRatio > 1000
        logScaledSensitivity = log10(scaledSensitivity + eps);
        highThreshold = 10^prctile(logScaledSensitivity, 70);
        mediumThreshold = 10^prctile(logScaledSensitivity, 30);
    else
        highThreshold = prctile(scaledSensitivity, 70);
        mediumThreshold = prctile(scaledSensitivity, 30);
    end

    high = scaledSensitivity >= highThreshold;
    medium = scaledSensitivity >= mediumThreshold & ...
             scaledSensitivity < highThreshold;
    low = scaledSensitivity < mediumThreshold;

    initialGroup(high) = {'High_Sensitivity'};
    initialGroup(medium) = {'Medium_Sensitivity'};
    initialGroup(low) = {'Low_Sensitivity'};

    assert(all(~cellfun(@isempty, initialGroup)), ...
           'Every parameter must receive a sensitivity classification.');

end
