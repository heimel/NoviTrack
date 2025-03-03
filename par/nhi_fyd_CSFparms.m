function par = nhi_fyd_CSFparms()
%database parameters
    par.User = 'dbuser_csf'; 
    par.Passw = 'b9DEaXrkW1My38Ea'; 
    par.Database = 'heimellab';
    par.Server = 'nhi-fyd.nin.knaw.nl';
    par.Tbl = 'sessions';
    par.Fields = { 'project', 'dataset', 'subject', 'stimulus', ...
                     'excond', 'setup', 'date', 'sessionid',  ...
                     'investid', 'logfile', 'url', 'server'};