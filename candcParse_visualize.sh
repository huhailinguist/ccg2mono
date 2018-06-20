#!/usr/bin/env bash
# use candc to parse sentences and visualize 
# install necessary packages to python3 by running in the command line:
# 
# ```pip3 install lxml simplejson pyyaml```
# 
# Then set the correct directory path on lines 18, 19, 20
#
# Hai Hu, Feb 2018

if [ "$#" -le 0 ]; then
    printf "\nUsage: ./candcParse_visualize.sh sentences.txt (outputDir)\n\n"
    exit 1
fi

# -------------------------------------------------
# set the following to the directories of CandC parser and ccg2lambda
candcBinDir="../candc-1.00/bin"
candcModelsDir="../candc-1.00/models"
ccg2lambdaDir="../ccg2lambda"
# -------------------------------------------------

if [ "$#" -eq 2 ]; then
    outputDir=$2
else
    outputDir="."
fi

# source ${ccg2lambdaDir}/py3/bin/activate

INname=$(basename "$1" .txt) # basename of input file
OUTname="tmp"
# for knowledge or sentences4k.txt
if [ $INname = "knowledge" ] || [ $INname = "sentences4k" ]; then
    OUTname=$INname
fi

# tokenize:
printf "tokenizing...\n"
cat $1 | sed -f ${ccg2lambdaDir}/en/tokenizer.sed > ${OUTname}.tok

# parse:
printf "parsing...\n"
${candcBinDir}/candc --models ${candcModelsDir} \
--candc-printer xml --input ${OUTname}.tok \
--output ${outputDir}/${OUTname}.candc.xml --log mylog

# convert to jigss
python3 ${ccg2lambdaDir}/en/candc2transccg.py \
${outputDir}/${OUTname}.candc.xml > ${outputDir}/${OUTname}.xml

# to html
python3 ${ccg2lambdaDir}/scripts/visualize.py \
${outputDir}/${OUTname}.xml > "${outputDir}/${OUTname}_candcParsed.html"

# deactivate

printf "Done!\n"
