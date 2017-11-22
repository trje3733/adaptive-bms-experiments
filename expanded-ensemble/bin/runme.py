__author__    = "Vivek Balasubramanian <vivek.balasubramanian@rutgers.edu>"
__copyright__ = "Copyright 2017, http://radical.rutgers.edu"
__license__   = "MIT"



from radical.entk import Pipeline, Stage, Task, AppManager, ResourceManager
import argparse, os, glob


## User settings
ENSEMBLE_SIZE=1    # Number of ensemble members / pipelines
TOTAL_ITERS=1       # Number of iterations to run current trial
SEED = 1            # Seed for stage 1


# ## Please leave the following as is, issue #3 needs to be resolved before modifying these
# ## The following are helpful if we divide our entire experiment of N iterations 
# ## over M trials due to (say) walltime limitations
# DONE=0              # Number of iterations already DONE
# ITER=[(DONE+1) for x in range(1, ENSEMBLE_SIZE+1)]      # Iteration number to start with
# DATA_LOC = ''       # Location where data from iterations 0 to DONE-1 is located


# ## Handling failed tasks
# FAILED=[False for x in range(1, ENSEMBLE_SIZE+1)]       


def get_pipeline(instance, iterations):

    # Create a Pipeline object
    p = Pipeline()

    # Create Stage 1
    s1 = Stage()

    # Create a Task
    t1 = Task()
    t1.pre_exec = ['module load python/2.7.7-anaconda']
    t1.executable = ['python']
    t1.arguments = ['analysis_1.py',
                    '--template', 'CB7G3_template.mdp', 
                    '--newname', 'CB7G3_run.mdp', 
                    '--wldelta', '2', 
                    '--equilibrated', 'False', 
                    '--lambda_state', '0', 
                    '--seed', '%s'%SEED]
    t1.cores = 1
    t1.copy_input_data = ['$SHARED/CB7G3_template.mdp','$SHARED/analysis_1.py']


    # Add the Task to the Stage
    s1.add_tasks(t1)

    # Add Stage to the Pipeline
    p.add_stages(s1)


    for it in range(1, iterations+1):

        # Create Stage 2
        s2 = Stage()

        # Create a Task
        t2 = Task()
        t2.pre_exec = ['source /home/trje3733/pkgs/gromacs/5.1.3.wlmod/bin/GMXRC.bash']
        t2.executable = ['gmx grompp']
        t2.arguments = ['-f', 'CB7G3_run.mdp', 
                        '-c', 'CB7G3.gro', 
                        '-p', 'CB7G3.top', 
                        '-n', 'CB7G3.ndx', 
                        '-o', 'CB7G3.tpr', 
                        '-maxwarn', '10']
        t2.cores = 1
        t2.copy_input_data = [
                                '$SHARED/CB7G3.ndx',
                                '$SHARED/CB7G3.top',
                                '$SHARED/3atomtypes.itp',
                                '$SHARED/3_GMX.itp',
                                '$SHARED/cucurbit_7_uril_GMX.itp'
                                ]

        if it == 0:
            t2.copy_input_data += [ '$Pipeline_%s_Stage_%s_Task_%s/CB7G3_run.mdp'%(p.uid, s1.uid, t1.uid), 
                                    '$SHARED/CB7G3.gro']
        else:
            t2.copy_input_data += [ '$Pipeline_%s_Stage_%s_Task_%s/CB7G3_run.mdp'%(p.uid, s4.uid, t4.uid), 
                                    '$Pipeline_%s_Stage_%s_Task_%s/CB7G3.gro'%(p.uid, s3.uid, t3.uid)]


        # Add the Task to the Stage
        s2.add_tasks(t2)

        # Add Stage to the Pipeline
        p.add_stages(s2)



        # Create Stage 3
        s3 = Stage()

        # Create a Task
        t3 = Task()
        t3.pre_exec = ['source /home/trje3733/pkgs/gromacs/5.1.3.wlmod/bin/GMXRC.bash']
        t3.executable = ['gmx mdrun']
        t3.arguments = ['-nt', 20, 
                        '-deffnm', 'CB7G3', 
                        '-dhdl', 'CB7G3_dhdl.xvg',]
        t3.cores = 20
        # t3.mpi = True
        t3.copy_input_data = ['$Pipeline_%s_Stage_%s_Task_%s/CB7G3.tpr'%(p.uid, s2.uid, t2.uid)]
        t3.copy_output_data = [ 'CB7G3_dhdl.xvg > $SHARED/CB7G3_run{1}_gen{0}_dhdl.xvg'.format(it,instance),
                                'CB7G3_pullf.xvg > $SHARED/CB7G3_run{1}_gen{0}_pullf.xvg'.format(it,instance),
                                'CB7G3_pullx.xvg > $SHARED/CB7G3_run{1}_gen{0}_pullx.xvg'.format(it,instance),
                                'CB7G3.log > $SHARED/CB7G3_run{1}_gen{0}.log'.format(it,instance)
                            ]
        t3.download_output_data = [ 'CB7G3.xtc > CB7G3_run{1}_gen{0}.xtc'.format(it, instance),
                                    'CB7G3.log > CB7G3_run{1}_gen{0}.log'.format(it,instance),
                                    'CB7G3_dhdl.xvg > CB7G3_run{1}_gen{0}_dhdl.xvg'.format(it,instance),
                                    'CB7G3_pullf.xvg > CB7G3_run{1}_gen{0}_pullf.xvg'.format(it,instance),
                                    'CB7G3_pullx.xvg > CB7G3_run{1}_gen{0}_pullx.xvg'.format(it,instance),
                                    'CB7G3.gro > CB7G3_run{1}_gen{0}.gro'.format(it, instance)
                                    ]

        # Add the Task to the Stage
        s3.add_tasks(t3)

        # Add Stage to the Pipeline
        p.add_stages(s3)



        # Create Stage 4
        s4 = Stage()

        # Create a Task
        t4 = Task()
        t4.pre_exec = [ 'module load python',
                        'export PYTHONPATH=/home/vivek91/modules/alchemical-analysis/alchemical_analysis:$PYTHONPATH',
                        'export PYTHONPATH=/home/vivek91/modules/alchemical-analysis:$PYTHONPATH',
                        'export PYTHONPATH=/home/vivek91/.local/lib/python2.7/site-packages:$PYTHONPATH',
                        'ln -s ../staging_area data']
        t4.executable = ['python']
        t4.arguments = [    '--newname=CB7G3_run.mdp',
                            '--template=CB7G3_template.mdp',
                            '--dir=./data',
                            #'--prev_data=%s'%DATA_LOC
                            '--gen={0}'.format(it, instance),
                            '--run={1}'.format(it, instance)
                        ]
        t4.cores = 1
        t4.link_input_data = [  '$SHARED/analysis_2.py',
                                '$SHARED/alchemical_analysis.py',
                                '$SHARED/CB7G3_template.mdp',
                            ]
        t4.download_output_data = [ 'analyze_1/results.txt > results_run{1}_gen{0}.txt'.format(it, instance),
                                    'STDOUT > stdout_run{1}_gen{0}'.format(it, instance),
                                    'STDERR > stderr_run{1}_gen{0}'.format(it, instance),
                                    'CB7G3_run.mdp > CB7G3_run{1}_gen{0}.mdp'.format(it, instance),
                                    'results_average.txt > results_average_run{1}_gen{0}.txt'.format(it, instance)
                                ]

        # Add the Task to the Stage
        s4.add_tasks(t4)

        # Add Stage to the Pipeline
        p.add_stages(s4)


    return p

if __name__ == '__main__':

    pipelines_set = set()

    for i in range(ENSEMBLE_SIZE):
        pipelines_set.add(get_pipeline(i, TOTAL_ITERS))

    total_cores = ENSEMBLE_SIZE*20

    # Create a dictionary describe four mandatory keys:
    # resource, walltime, cores and project
    # resource is 'local.localhost' to execute locally
    res_dict = {

            'resource': 'xsede.stampede',
            'walltime': 15,
            'cores': total_cores,
            'project': 'TG-MCB090174',
            'access_schema': 'gsissh'
    }


    # Download analysis file from MobleyLab repo
    os.system('curl -O https://raw.githubusercontent.com/MobleyLab/alchemical-analysis/master/alchemical_analysis/alchemical_analysis.py')


    # Create Resource Manager object with the above resource description
    rman = ResourceManager(res_dict)
    # Data common to multiple tasks -- transferred only once to common staging area
    rman.shared_data = [ './CB7G3.gro', './CB7G3.ndx', './CB7G3.top',
                        './CB7G3_template.mdp','./analysis_1.py',
                        './analysis_2.py', './determine_convergence.py',
                        './alchemical_analysis.py','./3atomtypes.itp',
                        './3_GMX.itp',
                        './cucurbit_7_uril_GMX.itp']

    # Create Application Manager
    appman = AppManager()
    #appman = AppManager(port=) # if using docker, specify port here.

    # Assign resource manager to the Application Manager
    appman.resource_manager = rman

    # Assign the workflow as a set of Pipelines to the Application Manager
    appman.assign_workflow(pipes_set)

    # Run the Application Manager
    appman.run()