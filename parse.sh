#!/usr/bin/env bash
# 1. use candc/easyccg to parse sentences
# 2. polarize
# 3. visualize
# install necessary packages to python3 by running in the command line:
# 
# ```pip3 install lxml simplejson pyyaml```
# 
# Then set the correct directory path on lines 21-25
#
# Hai Hu, Feb 2018

if [ "$#" -le 1 ]; then
    printf "\nUsage: ./parse.sh sentences.txt parser (outputDir)\n
      parser: candc, easyccg (if using easyccg, outputFormat is 'extended')\n\n"
    exit 1
fi

# -------------------------------------------------
# set the paths to CandC parser, easyccg parser and ccg2lambda
candc="../candc-1.00"
easyccg="../easyccg"
candcBinDir="../candc-1.00/bin"
candcModelsDir="../candc-1.00/models"
ccg2lambdaDir="../ccg2lambda"
# -------------------------------------------------

# outputDir
if [ "$#" -eq 3 ]; then
    outputDir=$3
else
    outputDir="."
fi

# INname, OUTname
INname=$(basename "$1" .txt) # basename of input file
OUTname="tmp"

# for knowledge or sentences4k.txt
if [ $INname = "knowledge" ] || [ $INname = "sentences4k" ]; then
    OUTname=$INname
fi

# parse
if [ $2 == "candc" ]; then
    ################  candc parser  ################
    printf "*** parsing using candc ***\n"

    # tokenize:
    printf "tokenizing...\n"
    cat $1 | sed -f ${ccg2lambdaDir}/en/tokenizer.sed > ${OUTname}.tok

    # parse:
    printf "parsing...\n"
    ${candcBinDir}/candc --models ${candcModelsDir} \
    --candc-printer xml --input ${OUTname}.tok \
    --output ${outputDir}/${OUTname}.candc.parsed.xml --log mylog

    # convert to transccg
    ./mytree2transccg.py candc > ${outputDir}/${OUTname}.candc2transccg.xml > \
    ${outputDir}/${OUTname}.candc2transccg.xml

    # convert to transccg
    # python3 ${ccg2lambdaDir}/en/candc2transccg.py \
    # ${outputDir}/${OUTname}.candc.parsed.xml > \
    # ${outputDir}/${OUTname}.candc2transccg.xml

    # to html
    python3 ${ccg2lambdaDir}/scripts/visualize.py \
    ${outputDir}/${OUTname}.candc2transccg.xml > \
    "${outputDir}/${OUTname}.candc_pretty.html"

else
    ################  easyccg parser  ################
    printf "*** parsing using easyccg ***\n"

    # tokenize, need to remove trailing space for each line:
    # need to remove punctuations for easyccg, otherwise there are
    # too many ways the punctuations can be combined in the tree
    printf "tokenizing...\n"
    cat $1 | ./${ccg2lambdaDir}/en/tokenizer.sed | \
    perl -pe 's/ \n/\n/g; s/ \.//g; s/ ,//g' > ${OUTname}.tok

    # get pos and ner using candc: (copied from easyccg README)
    cat ${OUTname}.tok | $candc/bin/pos --model $candc/models/pos | \
    $candc/bin/ner -model $candc/models/ner -ofmt "%w|%p|%n \n" > \
    "${outputDir}/${OUTname}.candc.pos.ner"

    # parse to text file: 
    cat "${outputDir}/${OUTname}.candc.pos.ner" | \
    java -jar $easyccg/easyccg.jar --model $easyccg/model_rebank -i POSandNERtagged -o extended --unrestrictedRules > \
    "${outputDir}/${OUTname}.easyccg.parsed.txt"

    # parse to easyccg html, which is hard to see
    # cat "${outputDir}/${OUTname}_candc.pos.ner" | java -jar $easyccg/easyccg.jar --model $easyccg/model_rebank -i POSandNERtagged -o html --unrestrictedRules > "${outputDir}/${OUTname}_easyccg.html"

    # change ( ) to {} so we can easily find nodes from easyccg output; IMPORTANT!
    sed -i -e 's/(</{</g; s/>)/>}/g; s/ )/ }/g' "${outputDir}/${OUTname}.easyccg.parsed.txt"

    # convert to transccg
    ./mytree2transccg.py easyccg > ${outputDir}/${OUTname}.easyccg2transccg.xml

    # convert to pretty html
    ${ccg2lambdaDir}/scripts/visualize.py \
    ${outputDir}/${OUTname}.easyccg2transccg.xml > \
    ${outputDir}/${OUTname}.easyccg_pretty.html

fi

printf "Done!\n"
