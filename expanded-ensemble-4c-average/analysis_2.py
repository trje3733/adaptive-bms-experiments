import pdb
import os
import numpy as np
import subprocess
import random
import glob
#import launchjob
import shutil
import argparse


def get_average_weight_data(logfiles, weight_size):
    """
    summary: uses log files to compute the average expanded ensemble weights

    input:
        logfiles (list) - names of the logs file to be used
        weight_size (int) - number of states
    output:
        weights_a (np.array) - array of time averaged weights
    """

    weights_temp = np.zeros([int(weight_size)])
    count = 0

    for log_file in logfiles:

        f = open(log_file, 'r')
        lines = f.readlines()
        f.close()

        wldelta = None
        time = None
        step = None
        next_line = 0
        weight_line = 0
        wl_max_hit = 1
        for l in lines:
            if 'Step           Time' in l:
                next_line = 1
            elif 'Wang-Landau incrementor is:' in l:
                vals = l.split(':')
                if wldelta is None:
                    wldelta = map(float, vals[1].split())
                else:
                    wldelta.extend(map(float, vals[1].split()))
            elif next_line is 1:
                vals = l.split()
                if time is None:
                    time = map(float, vals[1].split())
                    step = map(float, vals[0].split())
                else:
                    time.extend(map(float, vals[1].split()))
                    step.extend(map(float, vals[0].split()))
                next_line = 0
            elif 'N   FEPL  CoulL   VdwL  RestT    Count   G(in kT)  dG(in kT)' in l:
                weight_line = 1
                if wl_max_hit is 1:
                    count += 1
            elif weight_line is 1:
                if wl_max_hit is 1:
                    vals = l.split()
                    state = int(vals[0])
                    weight = float(vals[6])
                    if state is int(weight_size):
                        weight_line = 0
                    weights_temp[state-1] += weight
            else:
                next_line = 0

    weights_a = weights_temp / count
    return weights_a


def get_weights_from_mbar(free_energy_file):

    f = open(free_energy_file,'r')
    lines = f.readlines()
    f.close()
    weights = []
    for l in lines:
        if l[:9] == '   States':
            vals = l.split()
            # find which column is MBAR.
            i = 1
            for v in vals:
                if v[i] == 'MBAR':
                    mbar_column = i
                    i+=2
        else:
            if '+-' in l and '--' in l:
                vals = l.split()
                weights.append(vals[mbar_column])
                
    return np.array(weights)


def free_energy_analysis(dir, prev_data, filelist, template, new_mdp_name, run_number, gen_number):

    # run alchemical analysis on the expanded ensemble dhdl's
    # identify the dhdl files, copy them to a new directory, renaming if necessary, and figure out how many of them we should use
    dhdlfiles = glob.glob(os.path.join(dir,'*dhdl.xvg'))

    if prev_data:
        dhdlfiles.extend(glob.glob(os.path.join(prev_data, '*dhdl.xvg')))

    #maximum number of generations
    max_all_gens = 1000
    generations = []
    runs = []
    for d in dhdlfiles:
        vals = d.split('_')
        run = int(vals[1].replace('run',''))
        if run not in runs:
            runs.append(run)
        gen = int(vals[2].replace('gen',''))
        if gen not in generations:
            generations.append(gen)

    # now, what is the maximum generation for each of the runs.
    maxgens_per_run = np.zeros(len(runs))
    for d in dhdlfiles:
        vals = d.split('_')
        run = int(vals[1].replace('run',''))
        gen = int(vals[2].replace('gen',''))
        if gen > maxgens_per_run[runs.index(run)]:
            maxgens_per_run[runs.index(run)] = gen

    # which files to analyze? For now, ignore the 1/3 of the oldest, rounded up
    # 1 generation - ignore none
    # 2 generations - ignore 1, 
    # 3 generations - ignore 1, 
    # 4 generations - ignore 2, 
    maxgen = np.max(generations)
    analysis_cutoff = int(np.ceil(maxgen/2.0))
    if (analysis_cutoff - maxgen) < 1:
        analysis_cutoff = 0

    # which generations are going to be analyzed?    
    analysis_gens = []    
    for g in range(1,maxgen+1):
        if g > analysis_cutoff:
            analysis_gens.append(g)
            
    # figure out how many analyses have been done, make a new directory
    #analyses = glob.glob(os.path.join(dir,'analyze_*'))
    analyses = glob.glob(os.path.join('./','analyze_*'))
    max_analyses = 0
    for a in analyses:
        # remove if empty
        if not os.listdir(a):
            rmdir(a)
            continue
        vals = a.split('_')
        nanalyses = int(vals[1])
        if nanalyses > max_analyses:
            max_analyses = nanalyses
    analysis_dir = 'analyze' + '_' + str(max_analyses+1)
    #os.mkdir(os.path.join(dir, analysis_dir))
    os.mkdir(os.path.join('./', analysis_dir))

    # copy the dhdl files into a new directory, so we can just read all of them in the folder.
    for d in dhdlfiles:
        vals = d.split('_')
        run = int(vals[1].replace('run',''))
        gen = int(vals[2].replace('gen',''))
        if gen in analysis_gens:
            #folder = vals[0].split('/')[0]
            #print vals[0].split('/')
            newfile = vals[0].split('/')[2] + '_' + str(max_all_gens*run+gen) + '_dhdl.xvg'
            #absolute_analysis_dir = os.path.join(folder, analysis_dir)
            absolute_analysis_dir = os.path.join('./', analysis_dir)
            shutil.copyfile(d, os.path.join(absolute_analysis_dir,newfile))

    try:  # todo: ask if i should still be set to 1000
        subprocess.call(['python', 'alchemical_analysis.py', '--units', 'kBT', '-t', '300', '-d', absolute_analysis_dir, '-p', 'CB7G3_', '-x', '-i', '1000'])

    except:
        pass

    if not os.path.isfile(os.path.join(absolute_analysis_dir,'results.txt')):
        shutil.copyfile('results_bak.txt', os.path.join(absolute_analysis_dir,'results.txt'))
        print 'BACKUP USED'

    # open the file and read the weights (in units of kT)
    free_energy_file = os.path.join(absolute_analysis_dir, 'results.txt')
    f = open(free_energy_file, 'r')

        # Use the backup from last iteration
        #free_energy_file = os.path.join(os.path.basename(absolute_analysis_dir), '../results_bak.txt')

        # Move backup into analyze_1 folder so that staging doesn't fail
        #shutil.copyfile('results_bak.txt', os.path.join(absolute_analysis_dir,'results.txt'))
        #print 'BACKUP USED'
    
        #f = open(free_energy_file,'r')


    lines = f.readlines()
    # just use the MBAR total for the lines
    dweights = [0] # the first weight is always zero

    for l in lines:
        if 'States' in l:
            vals = l.split()
            #mbar_index = vals.index('MBAR')
            # little more complicated, but will always be doing MBAR for now, hard code for now.
            mbar_index = 18
        if ' -- ' in l:
            dweights.append(float(l.split()[mbar_index]))
    dweights = np.array(dweights)        
    weights = np.zeros(len(dweights))
    for i in range(0,len(weights)-1):
        weights[i+1] = weights[i] + dweights[i+1]

    # AVERAGE WEIGHT ANALYSIS- added by Travis Jensen
    # ------------------------------------------------------------------------------------------------------------------
    # run analysis on the expanded ensemble log files to determine new weights
    # identify the log files, copy them to a new directory, renaming if necessary,
    # and figure out how many of them we should use

    # copy the log files into a new directory, so we can just read all of them in the folder.
    for d in dhdlfiles:
        vals = d.split('_')
        run = int(vals[1].replace('run', ''))
        gen = int(vals[2].replace('gen', ''))
        if gen in analysis_gens:
            # rename to pull log instead of dhdl
            file_name = d.replace('_dhdl.xvg', '.log')
            # folder = vals[0].split('/')[0]
            # print vals[0].split('/')
            newfile = vals[0].split('/')[2] + '_' + str(max_all_gens * run + gen) + '.log'
            # absolute_analysis_dir = os.path.join(folder, analysis_dir)
            absolute_analysis_dir = os.path.join('./', analysis_dir)
            shutil.copyfile(file_name, os.path.join(absolute_analysis_dir, newfile))

    # run analysis on log files to generate new weights
    log_files = glob.glob(os.path.join(absolute_analysis_dir, 'CB7G3*.log'))
    weights = get_average_weight_data(log_files, weight_size=len(weights))

    # writing results to file
    log_results = open('results_average.txt', 'w')
    log_results.write(str(weights) + '\n')
    log_results.close()
    # ------------------------------------------------------------------------------------------------------------------

    # sort out the logfiles
    logs = []
    for f in filelist:
        if '.log' in f:
            logs.append(f)

    ilog = 0
    seedbase = random.randint(0, 100000000) # could replace by maxint (short integer)
    for l in logs:

        # we need to find the latest generation.
        vals = l.split('_')
        run = int(vals[1].replace('run',''))
        gen = int((vals[2].replace('gen','')).replace('.log',''))
        if gen != maxgens_per_run[runs.index(run)]:
            continue  # we only want to run the last generation, so if it's not the last one, don't bother here.

        # added by Travis Jensen to ensure proper gen and run are looked at
        if gen != int(gen_number):
            continue
        if run != int(run_number):
            continue

        [name, suffix] = l.split('.')[1:]
        name=name[1:]
        final_lambda_state, coupled_frames = get_info_from_dhdl(name + '_dhdl.xvg', trajectory_frequency=10) 
        # trajectory_frequency=10 corresponds to what we ran; should extract this automatically from the mdp.
        # it's just nstxout-compressed/nstdhdl
        equilibrated, wldelta, counts = get_info_from_logfile(l)
        seed = seedbase + ilog

        # extract the generation
        run_name = l.split('_')
        next_gen = int((run_name[2].split('.')[0]).replace('gen','')) + 1

        # new mdp name
        #new_mdp_name = run_name[0] + '_' + run_name[1] + '_' + 'gen' + str(next_gen) + '.mdp'

        # now we've extracted the information, create the start file for the next generation.
        generate_new_mdp(template, new_mdp_name, weights, wldelta, equilibrated, final_lambda_state, seed, counts)
        #vals = run_name[0].split('/')
        #new_gen_name = (new_mdp_name.replace('.mdp','')).split('/')[1]

        # print out for later the states that are coupled for configurational analysis
        f = open(name + '.states','w')
        for s in coupled_frames:
            f.write(str(s) + '\n')
        f.close()
            
        # launch the new jobs
        #launchjob.runonegen(new_gen_name, vals[0], new_mdp_name, name + '.gro', vals[1] + '.top', vals[1] + '.ndx')


def get_info_from_logfile(logfile):

    # read logfile lines
    f = open(logfile,'r')
    lines = f.readlines()
    f.close()    

    wldelta = None
    is_equilibrated = True

    all_vals = None
    lineno=0

    for l in lines:
        if 'Wang-Landau incrementor' in l:
            is_equilibrated = False 
            vals = l.split(':')
            wldelta = float(vals[1])

            # Grep all the vals in order to extract the count
            all_vals = lines[lineno+2:lineno+34]  # todo: change this to something that is not hard coded
                                                  # todo: fails if the number of states change
        lineno+=1

    # we don't break, because we need the LAST wldelta
        
    # Get the count column
    counts = []

    for row in all_vals:
        try:
            val = int(row.strip('\n').split()[4])
        except ValueError:
            val = 0
        counts.append(val)

    return is_equilibrated, wldelta, counts


def get_info_from_dhdl(dhdl, trajectory_frequency=None, coupled_states = [0,1,2,3]):

    # we want the final state, and a list of the frames with trajectories that are coupled.

    # read dhdl lines
    f = open(dhdl,'r')
    lines = f.readlines()
    f.close()

    # first, check the final state:

    # what's the last line?
    lastline = lines[-1]
    values = lastline.split()
    final_state = int(float(values[1])) # figure out why it's sometimes a float . . . 

    # next, if we are looking at the trajectories
    coupled_frames = []
    if trajectory_frequency != None:
        i = 0
        ilegend = 1
        stateindex = 1
        for l in lines:
            if l[0]!= '#' and l[0]!= '@':
                i+=1
                if i%trajectory_frequency == 0:
                    vals = l.split()
                    state = int(float(vals[stateindex]))
                    if state in coupled_states:
                        coupled_frames.append(i)
        coupled_frames = np.array(coupled_frames)

    return final_state, coupled_frames


def generate_new_mdp(template, new_mdp_name, weights, wldelta, equilibrated, init_lambda_state, seed, counts):

    '''
    inputs: 
       template (string): file name of the template that will be used to make the new generation
       new_mdp_name (string): the name of the new mpd.
       weights (array of floats): the new weights
       wldelta (float): the current wl delta
       equilibrated (bool): whether the weights are currently equilibrate
       init_lambda_state (int): the current lambda state
       seed (int): seed for this run
       counts (list of ints): count values from the last checkpoint to be used in the next iteration

    outputs: 
       none

    '''

    # read template lines
    f = open(template,'r')
    lines = f.readlines()
    f.close()

    f = open(new_mdp_name,'w')
    # write new mdp lines
    for l in lines:
        if 'REPLACE' in l:
            l = l.replace('REPLACELAMBDA',str(init_lambda_state)) 
            l = l.replace('REPLACEINITWLDELTA',str(wldelta)) 
            if equilibrated:
                l = l.replace('REPLACELMCSTATS','no')
            else:
                l = l.replace('REPLACELMCSTATS','wang-landau')
            l = l.replace('REPLACEGENSEED',str(seed))
            weights_array = ["%.3f" % w for w in weights]
            weights_string = ' '.join(weights_array)
            l = l.replace('REPLACEINITLAMBDAWEIGHTS',weights_string)
            counts_array = ["%d" % c for c in counts]
            counts_string = ' '.join(counts_array)
            l = l.replace('REPLACEINITCOUNTS',counts_string)
        f.write(l)


def configuration_analysis(dir, filelist):
    ''' 
    inputs
    dir (string) - the directory the files to analyze are found in
    name (string) - the common prefix of the files of interest
    filelist (array of strings) - a list of the files to analyze
    '''

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--newname', help='new name for reweighted mdp file')
    parser.add_argument('--template', help='name of template mdp file')
    parser.add_argument('--dir', help='path to data')
    parser.add_argument('--run', help='current run')
    parser.add_argument('--gen', help='current gen')
    parser.add_argument('--prev_data', help='path to data from previous iterations', default=None)
    args = parser.parse_args()

    dir = args.dir
    prev_data = args.prev_data
    #dir = './'
    filelist = glob.glob(os.path.join(dir,'CB7G3*'))

    if prev_data:
        filelist.extend(glob.glob(os.path.join(prev_data, 'CB7G3*')))

    #template = 'PLCpep7_template.mdp'
    free_energy_analysis(dir, prev_data, filelist, args.template, args.newname, args.run, args.gen)
