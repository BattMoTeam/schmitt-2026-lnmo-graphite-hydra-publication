function saveFigureSet(fig, outbase)

    figure(fig);
    drawnow;
    [folder, ~, ~] = fileparts(outbase);
    ensureFolder(folder);
    savefig(fig, [outbase, '.fig']);
    exportgraphics(fig, [outbase, '.png'], 'Resolution', 300);

end
