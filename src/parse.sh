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

USAGE="\nUsage: ./parse.sh sentences.txt parser (outputDir)\n
      parser can only be: candc, easyccg, depccg (if using easyccg, outputFormat is 'extended')\n\n"

if [ "$#" -le 1 ]; then
    printf "$USAGE"
    exit 1
fi

if [ $2 != "candc" ] && [ $2 != "easyccg" ] && [ $2 != "depccg" ]; then
    printf "$USAGE"
    exit 1
fi
# -------------------------------------------------
# set the paths to CandC parser, easyccg parser and ccg2lambda
candc="../../candc-1.00"
easyccg="../../easyccg"
candcBinDir="../../candc-1.00/bin"
candcModelsDir="../../candc-1.00/models"
ccg2lambdaDir="../../ccg2lambda"
# -------------------------------------------------

# outputDir
if [ "$#" -eq 3 ]; then
    outputDir=$3
else
    outputDir="."
fi

# INname, OUTname
INname=$(basename "$1" .txt) # basename of input file
# OUTname="tmp"

# for knowledge or sentences4k.txt
# if [ $INname = "knowledge" ] || [ $INname = "sentences4k" ]; then
#     OUTname=$INname
# fi
OUTname=$INname

# parse
if [ $2 == "candc" ]; then
    ################  candc parser  ################
    printf "*** parsing using candc ***\n"

    # tokenize:
    printf "tokenizing...\n"
    cat $1 | sed -f ${ccg2lambdaDir}/en/tokenizer.sed > ${OUTname}.tok

    # clean: at most n -> no
    ./preprocess.py ${OUTname}.tok

    # parse:
    printf "parsing...\n"
    ${candcBinDir}/candc --models ${candcModelsDir} \
    --candc-printer xml --input ${OUTname}.tok.clean \
    --output ${outputDir}/${OUTname}.candc.parsed.xml --log mylog

    # convert to transccg
    ./mytree2transccg.py "${outputDir}/${OUTname}.candc.parsed.xml" candc ${OUTname}.tok.preprocess.log \
    > ${outputDir}/${OUTname}.candc2transccg.xml > \
    ${outputDir}/${OUTname}.candc2transccg.xml

    # to html
    python ${ccg2lambdaDir}/scripts/visualize.py \
    ${outputDir}/${OUTname}.candc2transccg.xml > \
    "${outputDir}/${OUTname}.candc_pretty.html"

elif [ $2 == "easyccg" ]; then
    ################  easyccg parser  ################
    printf "*** parsing using easyccg ***\n"

    # tokenize, need to remove trailing space for each line:
    # need to remove punctuations for easyccg, otherwise there are
    # too many ways the punctuations can be combined in the tree
    printf "tokenizing...\n"
    cat $1 | ./${ccg2lambdaDir}/en/tokenizer.sed | \
    # perl -pe 's/ \n/\n/g; s/ \.//g; s/ ,//g' > ${OUTname}.tok  # remove ,
    perl -pe 's/ \n/\n/g; s/ \.//g;' > ${OUTname}.tok  # don't remove ,

    # clean: at most n -> no, output file: ${OUTname}.tok.clean
    ./preprocess.py ${OUTname}.tok

    # get pos and ner using candc: (copied from easyccg README)
    cat ${OUTname}.tok.clean | $candc/bin/pos --model $candc/models/pos | \
    $candc/bin/ner -model $candc/models/ner -ofmt "%w|%p|%n \n" > \
    "${outputDir}/${OUTname}.candc.pos.ner"

    # parse to text file:
    cat "${outputDir}/${OUTname}.candc.pos.ner" | \
    java -jar $easyccg/easyccg.jar --model $easyccg/model_rebank -i POSandNERtagged -o extended --unrestrictedRules > \
    "${outputDir}/${OUTname}.easyccg.parsed.txt"

    # parse to easyccg html, which is hard to see
    # cat "${outputDir}/${OUTname}.candc.pos.ner" | java -jar $easyccg/easyccg.jar --model $easyccg/model_rebank -i POSandNERtagged -o html --unrestrictedRules > "${outputDir}/${OUTname}_easyccg.html"

    # change ( ) to {} so we can easily find nodes from easyccg output; IMPORTANT!
    sed -i -e 's/(</{</g; s/>)/>}/g; s/ )/ }/g' "${outputDir}/${OUTname}.easyccg.parsed.txt"

    # convert to transccg
    ./mytree2transccg.py "${outputDir}/${OUTname}.easyccg.parsed.txt" easyccg  ${OUTname}.tok.preprocess.log \
    > ${outputDir}/${OUTname}.easyccg2transccg.xml

    # convert to pretty html
    python ${ccg2lambdaDir}/scripts/visualize.py \
    ${outputDir}/${OUTname}.easyccg2transccg.xml > \
    ${outputDir}/${OUTname}.easyccg_pretty.html

elif [ $2 == "depccg" ]; then
    ################  depccg parser  ################
    printf "*** parsing using depccg ***\n"

    # tokenize, need to remove trailing space for each line:
    # remove punctuations for depccg
    printf "tokenizing...\n"
    cat $1 | ./${ccg2lambdaDir}/en/tokenizer.sed | \
    perl -pe 's/ \n/\n/g; s/ \.//g; s/ ,//g' > ${OUTname}.tok

    # clean: at most n -> no, output file: ${OUTname}.tok.clean
    ./preprocess.py ${OUTname}.tok

    # parse to text file using depccg (now using rebanked CCG model)
    cat ${OUTname}.tok.clean | python -m depccg en --model elmo_rebank -f auto_extended -a spacy > \
    "${outputDir}/${OUTname}.depccg.parsed.txt"

    # change ( ) to {} so we can easily find nodes from easyccg output; IMPORTANT!
    sed -i -e 's/(</{</g; s/>)/>}/g; s/ )/ }/g' "${outputDir}/${OUTname}.depccg.parsed.txt"

    # convert to transccg
    ./mytree2transccg.py "${outputDir}/${OUTname}.depccg.parsed.txt" depccg  ${OUTname}.tok.preprocess.log \
    > ${outputDir}/${OUTname}.depccg2transccg.xml

    # convert to pretty html
    python ${ccg2lambdaDir}/scripts/visualize.py \
    ${outputDir}/${OUTname}.depccg2transccg.xml > \
    ${outputDir}/${OUTname}.depccg_pretty.html

else

    printf "parser not supported\ntry one of: candc, easyccg, depccg\n"

fi

printf "Done!\n"
