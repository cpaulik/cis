#!/bin/bash -e

SUBJECT=iriscontourf

#########################################
# Code in this section not to be modified.
#########################################
# The current directory.
TEST_DIR=`pwd`
# The full path of the directory containing the common build and run scripts.
ROOT_TEST_DIR="${TEST_DIR}/.."

source_dir="${ROOT_TEST_DIR}/test_files/"

rm -f "O$SUBJECT.png"
# load in the standard functions
. "$TEST_DIR/CommonFunctions.sh"
########################################

#################################
# Place the execution lines below.
#
#################################
start_time="$(date +%s)"

cis plot rain:${source_dir}xglnwa.pm.k8dec-k9nov.col.tm.nc --type contourf --ylabel "Overidden Y Label" --height 5 --width 10 --ymin 15 --ymax 45 --ystep 10 --nocolourbar --output "O$SUBJECT.png"

end_time="$(($(date +%s)-start_time))"
echo "Time taken: ${end_time}s"
#################################
#
# Call standard function that compares the results and removes and unnecessary files
CompareResultsAndClean
# exit code is 0 for success and 1 for failure.
exit $COMPARE_RESULTS_RETURN_VALUE

######################### END OF SCRIPT ####################################
