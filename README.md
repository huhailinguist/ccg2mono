# ccg2mono
Authors: Hai Hu, Larry Moss

## Description
This program takes CCG parses of sentences (from C&C parser) and add monotonicity information to every constituent.

For example:

- input sentence: No man who likes every dog sleeps. 

- output: No&uarr; man&darr; who&darr; likes&darr; every&darr; dog&uarr; sleeps&darr; .&uarr;

## Preparation
You need several things to run our program.

1. Install [C&C parser](http://www.cl.cam.ac.uk/~sc609/candc-1.00.html). You can just download the precompiled binaries and the models (models trained on CCGbank 02-21 and MUC 7, 50MB) from the webpage. Then copy the paths of the binaries and models to lines 18 and 19 in *candcParse\_visualize.sh*.

2. Clone the repo [ccg2lambda](https://github.com/mynlp/ccg2lambda) to your machine. Copy the path of ccg2lambda to line 20 in *candcParse\_visualize.sh*.

3. Install some python packages (for visualizing trees in ccg2lambda) by typing `pip3 install lxml simplejson pyyaml`.

Then you are ready to go. 

## getMono

*getMono.py* takes in CCG parse trees and polarize each constituent. 

To do so, first put your sentence in a file (e.g. test). Then type the following to parse the sentences using C&C parser:

```bash
./candcParse_visualize.sh test
```

There will be two important output files: *test_candcParsed.html* and *tmp.xml*.

- *test_candcParsed.html* is a visualiztion of the parse trees. You can check whether the sentences are parsed correctly by just using a browser to open the file.

- *tmp.xml* contains the xml format of the parses, which our program work with.

Now you can run 

```bash
./getMono.py (sentNo) (-vall for verbose, i.e. print the trees)
``` 

and get the monotonicity of your sentences in STDOUT. For commandline parameters of this python script, please type `./getMono.py -h`

## infer
*infer.py* first reads in 3 knowledge representations from the folder k:

- pairs.txt: dog < animal, beat < touch, etc.
- subsecAdj.txt: subsective adjectives such as good, bad, tall, etc.
- sentences4k.txt: sentences with "isA" relations such as "John is a cat."

It will then build a knowledge base on the above information (see our second paper
 below for details).
 
Finally, it will do inference using simple substitution, or replacement. 
Thus if the input sentence is "every&uarr cat&darr likes&uarr some&uarr good&uarr dog&uarr",
one replacement will result in inferences such as:

- every&uarr cat&darr likes&uarr some&uarr good&uarr animal&uarr
- every&uarr cat&darr likes&uarr some&uarr dog&uarr

two replacements will result in:

- every&uarr cat&darr likes&uarr some&uarr animal&uarr 

## TODO
Add visualization to the final monotonicity output.
Handle more cases in inference.

## Cite
```
@InProceedings{humoss2018,
  author    = {Hu, Hai and Moss, Lawrence S.},
  title     = {Polarity Computations in Flexible Categorial Grammar},
  booktitle = {Proceedings of the 7th Joint Conference on Lexical and Computational Semantics (*SEM 2018)},
  year      = {2018},
  address   = {New Orleans, US},
  publisher = {Association for Computational Linguistics}
}
```

Or this which has a description of how _inference_ work in our system:
 
```
@InProceedings{humoss2018,
  author    = {Hu, Hai and Icard III, Thomas and Moss, Lawrence S.},
  title     = {Automated Reasoning from Polarized Parse Trees},
  booktitle = {Proceedings of the Fifth Workshop on Natural Language and Computer Science},
  year      = {2018},
  address   = {Oxford, England}
}
```

