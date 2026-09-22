function compareHessians(Hscaled, HfdScaled, HfdReport, Xopt, shortnames)
% Compare a BFGS Hessian with finite-difference Hessians calculated at several step sizes.

    Xopt = Xopt(:);
    shortnames = shortnames(:);
    hessianSteps = HfdReport.perturbationSizes;
    numSteps = numel(hessianSteps);
    relErr = zeros(numSteps, 1);
    maxAbsErr = zeros(numSteps, 1);
    fdeigenvals = zeros(numel(Xopt), numSteps);
    eigenvalsBFGS = eig(Hscaled, 'vector');

    for stepno = 1:numSteps
        Hfd = HfdScaled(:, :, stepno);
        Hdiff = Hscaled - Hfd;

        relErr(stepno) = norm(Hdiff, 'fro') ./ max(norm(Hfd, 'fro'), eps);
        maxAbsErr(stepno) = max(abs(Hdiff), [], 'all');
        fdeigenvals(:, stepno) = sort(eig(Hfd));
    end

    Hcomparison = HfdReport.summary;
    Hcomparison.relErrToBFGS = relErr;
    Hcomparison.maxAbsErr = maxAbsErr;
    disp('Finite-difference Hessian comparison:');
    disp(Hcomparison);
    fprintf('Gradient evaluations for finite-difference Hessians: %d\n', HfdReport.numberOfGradientEvaluations);

    stencilTable = cell2table(HfdReport.schemes, 'VariableNames', compose("h=%g", hessianSteps), 'RowNames', shortnames);
    disp('Finite-difference stencil by parameter:');
    disp(stencilTable);

    eigenvalueComparison = table((1:numel(Xopt))', eigenvalsBFGS, 'VariableNames', {'Mode', 'BFGS'});
    for stepno = 1:numSteps
        varname = matlab.lang.makeValidName(sprintf('FD_h_%g', hessianSteps(stepno)));
        eigenvalueComparison.(varname) = fdeigenvals(:, stepno);
    end
    disp('Hessian eigenvalue comparison:');
    disp(eigenvalueComparison);

    boundtol = 1e-8;
    freeParams = Xopt > boundtol & Xopt < 1 - boundtol;
    activeParams = ~freeParams;

    if any(activeParams)
        activeParameterTable = table(shortnames(activeParams), Xopt(activeParams), ...
            'VariableNames', {'Parameter', 'ScaledValue'});
        disp('Parameters active at a unit-box bound:');
        disp(activeParameterTable);
    end

    fprintf('Free parameters for reduced-Hessian analysis: %d/%d\n', nnz(freeParams), numel(Xopt));
    if any(freeParams)
        for stepno = 1:numSteps
            Hreduced = HfdScaled(freeParams, freeParams, stepno);
            reducedEigenvalues = eig(Hreduced);
            fprintf('FD reduced Hessian h=%g: min eigenvalue=%g, max eigenvalue=%g\n', ...
                hessianSteps(stepno), min(reducedEigenvalues), max(reducedEigenvalues));
        end
    end

end
