#     analyse_solid_run.py: analyse and report on SOLiD sequencer runs
#     Copyright (C) University of Manchester 2011 Peter Briggs
#
########################################################################
#
# analyse_solid_run.py
#
#########################################################################

"""analyse_solid_run.py

Provides functionality for analysing a SOLiD run, to report slide layout
etc, and suggest a layout for the analysis directories.

To do this it looks at grouping 'projects' (which are groups of libraries)
into 'experiments'. The heuristics for this are rather convoluted as
they are based on the names of the libraries.
"""

#######################################################################
# Import modules that this module depends on
#######################################################################

import sys
import os
import string
import SolidDataExtractor
import Spreadsheet

#######################################################################
# Class definitions
#######################################################################

class SolidExperiment:
    """Class describing an experiment from a SOLiD run.

    An experiment in this context is a collection of libraries
    which might come from one or more samples, but which will
    be grouped together in a common analysis directory.

    Data about the experiment can be accessed via the object's
    properties, specifically:
        
    projects: a list of SolidProject objects
    solid_run: the associated SolidRun object (or None)

    Other data can be accessed via the object's methods.
    """

    def __init__(self,project=None,run=None):
        """Create a new SolidExperiment instance

        Arguments:
          project: (optional) a SolidProject object to add to
            the experiment
          run: (optional) a SolidRun to associate with the
            experiment
        """
        self.projects = []
        if project:
            self.addProject(project)
        self.analysis_dir = ""
        self.solid_run = run

    def addProject(self,project):
        """Add a project to the experiment.

        project is a populated SolidProject object.
        """
        self.projects.append(project)

    def prefixes(self):
        """Return a list of prefixes from all libraries in the experiment.
        """
        prefixes = []
        for project in self.projects:
            for lib in project.libraries:
                if not lib.prefix in prefixes:
                    prefixes.append(lib.prefix)
        prefixes.sort()
        return prefixes

    def getExperimentName(self):
        """Return the name for the experiment.

        If all libraries in the experiment share a common prefix
        then the experiment name will be '<prefix>_expt'. Otherwise
        the initials of the experimenter are used: <initials>_expt.
        """
        if len(self.prefixes()) > 1:
            # Multiple prefixes, use the experimenter's name
            return self.projects[0].name+'_expt'
        elif len(self.prefixes()) == 1:
            # Single prefix, use that
            return self.prefixes()[0].strip("_")+'_expt'
        else:
            # No prefixes
            return "UNKNOWN_expt"

    def getAnalysisDir(self,suffix=''):
        """Return the name of the analysis directory for the experiment.

        The analysis directory name will be the name of the SOLiD run
        directory with '_analysis' appended. If a suffix is supplied then
        this will also be appended.

        If a suffix is not supplied then the last constructed directory
        name is returned.
        """
        # If an analysis directory was already set and
        # no suffix was specified then return it
        if self.analysis_dir and not suffix:
            return self.analysis_dir
        # Otherwise construct the name from scratch
        if self.projects:
            self.analysis_dir = os.path.join(self.projects[0].\
                                                 getRun().run_dir+'_analysis_test',
                                             self.getExperimentName())
            if suffix:
                self.analysis_dir += str(suffix)
            return self.analysis_dir
        else:
            return ''

    def getAnalysisFileName(self,filen,sample_name):
        """Return the 'analysis' file name based on a source file name.

        Source file names are typically of the form:
        solid0127_20110419_FRAG_BC_<sample>_F3_<library>.csfasta

        The analysis file will be the same except:
        1. The <sample> name is removed, and
        2. If the <sample> name includes "_rpt" then append this
           to the filename.

        Note that the sample name must be explicitly provided
        as a single SolidExperiment may be made up of multiple
        projects with libraries from different projects.

        Arguments:
          filen: name of the source file
          sample_name: sample name that the source file comes from

        Returns:
          Name for the analysis file.
        """
        # Construct new name by removing the sample name
        analysis_filen = replace_string(filen,sample_name+'_')
        # If sample name contains "rpt" then append to the new file name
        if sample_name.find('_rpt') > -1:
            analysis_filen = os.path.splitext(analysis_filen)[0]+\
                '_rpt'+os.path.splitext(analysis_filen)[1]
        return analysis_filen

#######################################################################
# Module Functions: utilities
#######################################################################

def banner(title):
    """Write a banner for a section of output

    Given some text as 'title", print this framed by '='s."""

    decoration = ''.join(['=' for i in range(len(title))])
    print "%s" % decoration
    print "%s" % title
    print "%s\n" % decoration

def replace_string(s,replace_substr,with_str=''):
    """Do query/replace on a string

    Arguments:
      s: original string
      replace_substr: substring in s to be replaced
      with_str: (optional) string to substitute replace_substring by

    Returns:
      Modified string
    """
    s1 = s
    slen = len(replace_substr)
    while True:
        try:
            i = s1.rindex(replace_substr)
            s1 = s1[0:i]+str(with_str)+s1[i+slen:]
        except ValueError:
            return s1

#######################################################################
# Module Functions: SOLiD data utilities
#######################################################################

def get_experiments(solid_runs):
    """Organise SolidProjects into SolidExperiments.

    Given a set of solid runs, organises the 'project' data into
    'experiments' by associating projects together. The organisation
    is done by looking at the names.

    This is necessary if a single experiment was split across two flow
    cells.

    Arguments:
      solid_runs: a list or tuple of SolidRun objects to report.

    Returns:
      List of SolidExperiment objects.
    """
    # Organise projects into experiments
    experiments = []
    for run in solid_runs:
        for sample in run.samples:
            for project in sample.projects:
                # Create experiment for this project
                expt = SolidExperiment(project,run=run)
                # Have we seen something similar before?
                match_previous_expt = False
                for prev_expt in experiments:
                    if expt.prefixes() == prev_expt.prefixes():
                        # Combine these experiments
                        prev_expt.addProject(project)
                        match_previous_expt = True
                        break
                # No match
                if not match_previous_expt:
                    experiments.append(expt)

    # Set analysis directory names
    analysis_dirs = []
    for expt in experiments:
        # Analysis directory
        index = 1
        dirn = expt.getAnalysisDir()
        while os.path.basename(dirn) in analysis_dirs:
            index += 1
            dirn = expt.getAnalysisDir("_%s" % index)
        analysis_dirs.append(os.path.basename(dirn))

    # Finished
    return experiments

def pretty_print_libraries(libraries):
    """Given a list of libraries, format for pretty printing.

    Examples:
    ['DR1', 'DR2', 'DR3', DR4'] -> 'DR1-4'
    """
    # Split each library name into prefix and numeric suffix
    ##print "pretty_print: input = "+str(libraries)
    libs = sorted(libraries, key=lambda l: (l.prefix,l.index))
    ##print str(libs)
    # Go through and group
    groups = []
    group = []
    last_index = None
    for lib in libs:
        # Check if this is next in sequence
        try:
            if lib.index == last_index+1:
                # Next in sequence
                group.append(lib)
                last_index = lib.index
                continue
        except TypeError:
            # One or both of the indexes was None
            pass
        # Current lib is not next in previous sequence
        # Tidy up and start new group
        if group:
            groups.append(group)
        group = [lib]
        last_index = lib.index
    # Capture last group
    if group:
        groups.append(group)
    ##print str(groups)
    # Pretty print
    out = []
    for group in groups:
        if len(group) == 1:
            # "group" of one
            out.append(group[0].name)
        else:
            # Group with at least two members
            out.append(group[0].name+"-"+group[-1].index_as_string)
    # Concatenate and return
    return ', '.join(out)

def get_slide_layout(solid_run):
    """Return description of slide layout for a SOLiD run.

    Given a SolidRun object 'solid_run', return the slide layout
    description (e.g. "whole slide", "quads" etc) as a string, based
    on the number of samples in the run.
    """
    if len(solid_run.samples) == 1:
        return "Whole slide"
    elif len(solid_run.samples) == 4:
        return "Quads"
    elif len(solid_run.samples) == 8:
        return "Octets"
    else:
        return "Undefined layout"

#######################################################################
# Module Functions: filesystem wrappers
#######################################################################

def mkdir(dirn):
    """Make a directory"""
    print "Making %s" % dirn
    if not os.path.isdir(dirn):
        os.mkdir(dirn)

def mklink(target,link_name):
    """Make a symbolic link"""
    print "Linking to %s from %s" % (target,link_name)
    os.symlink(target,link_name)

#######################################################################
# Module Functions: program functions
#######################################################################

def report_run(solid_runs):
    """Print a brief report about SOLiD runs.

    This generates a brief screen report about the content of the
    supplied SOLiD runs e.g. flow cells, layout, number of samples
    etc.

    Arguments:
      solid_runs: a list or tuple of SolidRun objects to report.
    """
    # Report the data for each run
    banner("REPORT RUNS")
    for run in solid_runs:
        # Report overall slide layout
        slide_layout = get_slide_layout(run)
        print "FC%s (%s)" % (str(run.run_info.flow_cell),
                               str(slide_layout))
        print "Date: %s" % (run.run_info.date)
        print "I.D.: %s\n" % (run.run_info.name)
        #
        # Report projects for each sample
        for sample in run.samples:
            for project in sample.projects:
                libraries = pretty_print_libraries(project.libraries)
                print "Sample %s: (project %s): %s" % (sample,
                                                         project.name,
                                                         libraries)
                if run.run_info.is_barcoded_sample:
                    print "B/C samples: %d" % len(project.libraries)
                total_reads = 'not available'
                if sample.barcode_stats:
                    try:
                        total_reads = sample.barcode_stats.\
                            getDataByName("All Beads")[-1]
                    except IndexError:
                        pass
                # FIXME need to check that this total read info is
                # actually correct
                print "Total reads: %s\n" % str(total_reads)

def write_spreadsheet(solid_runs,spreadsheet):
    """Generate or append run data to an XLS-format spreadsheet

    Creates a new spreadsheet or appends to an existing one, writing
    new rows to summarise the data about the solid runs supplied as
    input.

    Arguments:
      solid_runs: a list or tuple of SolidRun objects to report.
      spreadsheet: the name of the XLS-format spreadsheet to write
        the data
    """
    banner("WRITE SPREADSHEET")

    # Check whether spreadsheet file already exists
    if os.path.exists(spreadsheet):
        write_header = False
    else:
        write_header = True

    # Only write date once
    write_date = True

    # Open spreadsheet
    wb = Spreadsheet.Spreadsheet(spreadsheet,'SOLiD Runs')

    # Header row
    if write_header:
        wb.addTitleRow(['Ref No',
                        'Project Description',
                        'P.I.',
                        'Date',
                        'Library type',
                        'Sample & Layout Description',
                        'B/C samples',
                        'Total reads',
                        'I.D.',
                        'Cost'])
    
    # Spacer row
    wb.addEmptyRow(color='gray25')

    # Report the data for each run
    for run in solid_runs:
        # First line: date, flow cell layout, and id
        slide_layout = get_slide_layout(run)
        description = "FC"+str(run.run_info.flow_cell)+" ("+slide_layout+")"
        # Barcoding status
        # Assumes all samples/libraries in the project have the same
        # barcoding status
        try:
            is_barcoded = run.samples[0].projects[0].isBarcoded()
        except IndexError:
            is_barcoded = False
        # Run with only one sample
        total_reads = ''
        if len(run.samples) == 1:
            description += ": "+str(run.samples[0].name)
            try:
                if run.samples[0].projects[0].isBarcoded():
                    # Barcoded sample, get stats
                    try:
                        total_reads = run.samples[0].barcode_stats.\
                            getDataByName("All Beads")[-1]
                    except AttributeError:
                        # Potential problem
                        total_reads = "NOT_FOUND"
                else:
                    # Not a barcoded sample
                    total_reads = "MANUAL_LOOKUP"
            except IndexError:
                # Some problem looking up barcode status
                total_reads = "NO_INFO"
        # Deal with date string
        if write_date:
            run_date = run.run_info.date
            write_date = False # Don't write date again
        else:
            run_date = ''
        run_id = run.run_info.name
        wb.addRow(['',
                   '',
                   '',
                   run_date,
                   '',
                   description,
                   '',
                   total_reads,
                   run_id])
        # Add one line per project in each sample
        index = 0
        for sample in run.samples:
            for project in sample.projects:
                libraries = pretty_print_libraries(project.libraries)
                experimenters_initials = project.libraries[0].initials
                # Get initial description and total reads
                if len(run.samples) > 1:
                    # Multiple samples in one project
                    description = sample.name+": "
                    # Total reads
                    # For barcoded samples we should be able to extract
                    # thos from the barcode statistics data
                    if project.isBarcoded():
                        total_reads = ''
                        if sample.barcode_stats:
                            try:
                                total_reads = sample.barcode_stats.\
                                    getDataByName("All Beads")[-1]
                            except IndexError:
                                pass
                    else:
                        # Not a barcoded sample, manual lookup
                        total_reads = "MANUAL_LOOKUP"
                else:
                    # All libraries belong to the same sample
                    description = ''
                    # Total reads already written once
                    total_reads = ''
                # Library type
                if project.isBarcoded():
                    library_type = "bar-coding"
                else:
                    library_type = ''
                # Add samples to the libraries
                description += str(len(project.libraries))+" samples "+\
                    libraries
                # Project description field
                # Essentially a placeholder with experimenter's initials
                project_description = "%s) %s [project description]" % \
                    (string.lowercase[index],experimenters_initials)
                index += 1
                # FIXME need to check that this total read info is
                # actually correct
                wb.addRow(['',
                           project_description,
                           '[P.I.]',
                           '',
                           library_type,
                           description,
                           len(project.libraries),
                           total_reads])
                wb.addEmptyRow()
                
    # Write the spreadsheet
    wb.write()

def suggest_analysis_layout(experiments):
    """Print a suggested analysis directory scheme

    Given a set of SolidExperiments, print a suggested layout scheme
    for the analysis directory including names and partitioning of
    primary data (i.e. which data files should be associated with which
    subdirectory).

    Arguments:
      experiments: a list of SolidExperiment objects.
    """
    # Suggest an analysis directory and file naming scheme
    banner("SUGGESTED ANALYSIS LAYOUT SCHEME")
    for expt in experiments:
        # Analysis directory
        dirn = expt.getAnalysisDir()
        print dirn
        # Primary data files
        files = []
        for project in expt.projects:
            for library in project.libraries:
                ln_csfasta = expt.\
                    getAnalysisFileName(os.path.basename(library.csfasta),
                                        library.parent_sample.name)
                ln_qual = expt.\
                    getAnalysisFileName(os.path.basename(library.qual),
                                        library.parent_sample.name)
                print "* %s: %s" % (library,ln_csfasta)
                print "* %s: %s" % (library,ln_qual)
                if ln_csfasta in files or ln_qual in files:
                    print "*** WARNING duplicated file name! ***"
                files.append(ln_csfasta)
                files.append(ln_qual)
            print ""

def build_analysis_dir(experiments):
    """Build analysis directories for the supplied experiments.

    This performs the following operations:

    1. Make the top level analysis directory for each run directory
    2. Create a "data" subdirectory with links to all primary data
    3. Create subdirectories for each experiment
    4. Within each subdirectory create "data" subdirectory with links
       to the primary data files for that experiment

    Arguments:
      experiments: list of SolidExperiments.
    """
    # Suggest an analysis directory and file naming scheme
    banner("BUILD ANALYSIS DIRECTORY")
    # Top-level analysis directory
    analysis_dir = experiments[0].solid_run.run_dir+"_analysis_test"
    if os.path.exists(analysis_dir):
        print "Analysis directory already exists, build aborted"
        return
    mkdir(analysis_dir)
    # Top-level data directory
    all_data_dir = os.path.join(analysis_dir,"data")
    mkdir(all_data_dir)
    # Link to all primary data files from a single directory
    for expt in experiments:
        for project in expt.projects:
            for library in project.libraries:
                ln_csfasta = os.path.join(
                    all_data_dir,
                    expt.getAnalysisFileName(os.path.basename(library.csfasta),
                                             library.parent_sample.name))
                mklink(library.csfasta,ln_csfasta)
                ln_qual = os.path.join(
                    all_data_dir,
                    expt.getAnalysisFileName(os.path.basename(library.qual),
                                             library.parent_sample.name))
                mklink(library.qual,ln_qual)
    # Directories for each experiment
    for expt in experiments:
        # Make an analysis directory for this experiment
        expt_dir = os.path.join(analysis_dir,expt.getExperimentName())
        mkdir(expt_dir)
        files = []
        duplicated_files = []
        # Make links to primary data
        for project in expt.projects:
            for library in project.libraries:
                ln_csfasta = os.path.join(expt_dir,
                                          os.path.basename(library.csfasta))
                ln_qual = os.path.join(expt_dir,
                                       os.path.basename(library.qual))
                mklink(library.csfasta,ln_csfasta)
                mklink(library.qual,ln_qual)
                # Check for duplicated names
                # This is an error
                if ln_csfasta in files:
                    print "*** WARNING duplicated file name! ***"
                    duplicated_files.append(ln_csfasta)
                else:
                    files.append(ln_csfasta)
                if ln_qual in files:
                    print "*** WARNING duplicated file name! ***"
                    duplicated_files.append(ln_csfasta)
                else:
                    files.append(ln_qual)
    # Done
    return

#######################################################################
# Main program
#######################################################################

if __name__ == "__main__":
    # Get solid directories
    if len(sys.argv) < 2:
        print "Usage: python %s [OPTIONS] <solid_run_dir>" % sys.argv[0]
        print ""
        print "Various operations on a SOLiD run directory. Note that if"
        print "<solid_run_dir>_2 also exists then this is automatically"
        print "detected and included in the processing."
        print ""
        print "Options:"
        print "  --report: print a report of the SOLiD run"
        print "  --layout: suggest layout for analysis directories"
        print "  --spreadsheet[=<file>.xls]: write report to Excel spreadsheet"
        print "  --build-layout: construct analysis directories for the run"
        sys.exit()

    # Solid run directories
    solid_dir_fc1 = sys.argv[-1]
    solid_dir_fc2 = sys.argv[-1]+"_2"
    if os.path.isdir(solid_dir_fc2):
        solid_dirs = (solid_dir_fc1,solid_dir_fc2)
    else:
        solid_dirs = (solid_dir_fc1,)

    # Other options
    do_report_run = False
    if "--report" in sys.argv[1:-1]:
        do_report_run = True

    do_suggest_layout = False
    if "--layout" in sys.argv[1:-1]:
        do_suggest_layout = True

    do_spreadsheet = False
    for arg in sys.argv[1:-1]:
        if arg.startswith("--spreadsheet"):
            do_spreadsheet = True
            try:
                i = arg.index("=")
                spreadsheet = arg[i+1:]
            except IndexError:
                spreadsheet = solid_dir_fc1+".xls"
            print "Writing spreadsheet %s" % spreadsheet

    do_build_layout = False
    if "--build-layout" in sys.argv[1:-1]:
        do_build_layout = True

    # Get the run information
    solid_runs = []
    for solid_dir in solid_dirs:
        run = SolidDataExtractor.SolidRun(solid_dir)
        if not run:
            print "Error extracting run data for %s" % solid_dir
        else:
            solid_runs.append(run)

    # Report the runs
    if do_report_run:
        report_run(solid_runs)

    # Report the runs to a spreadsheet
    if do_spreadsheet:
        write_spreadsheet(solid_runs,spreadsheet)

    # Determine experiments
    if do_suggest_layout or do_build_layout:
        experiments = get_experiments(solid_runs)
        # Suggest a layout
        if do_suggest_layout:
            suggest_analysis_layout(experiments)
        # Build the layout
        if do_build_layout:
            build_analysis_dir(experiments)
        

