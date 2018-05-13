#!/usr/bin/env bash
# use candc to parse sentences and visualize 
# install necessary packages to python3 by running in the command line:
# 
# ```pip3 install lxml simplejson pyyaml```
# 
# Then set the correct directory path on lines 18, 19, 20
#
# Hai Hu, Feb 2018

if [ "$#" -ne 1 ]; then
    printf "\nUsage: ./candcParse_visualize.sh sentences.txt\n\n"
    exit 1
fi

# -------------------------------------------------
# set the following to the directories of CandC parser and ccg2lambda
candcBinDir="/media/hai/G/tools/CandCparser/candc-1.00-compiled/bin"
candcModelsDir="/media/hai/G/tools/CandCparser/models"
ccg2lambdaDir="/media/hai/G/tools/ccg2lambda"
# -------------------------------------------------

# source ${ccg2lambdaDir}/py3/bin/activate

# tokenize:
printf "tokenizing...\n"
cat $1 | sed -f ${ccg2lambdaDir}/en/tokenizer.sed > tmp.tok

# parse:
printf "parsing...\n"
${candcBinDir}/candc --models ${candcModelsDir} \
--candc-printer xml --input tmp.tok > tmp.candc.xml

# convert to jigss
python3 ${ccg2lambdaDir}/en/candc2transccg.py tmp.candc.xml > tmp.xml

# to html
python3 ${ccg2lambdaDir}/scripts/visualize.py tmp.xml > "$1_candcParsed.html"

# deactivate

# for knowledge
if [ $1 = "knowledge" ]; then
    mv tmp.candc.xml knowledge.candc.xml
fi

printf "Done!\n"
