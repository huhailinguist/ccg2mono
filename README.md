# ccg2mono
Authors: Hai Hu, Larry Moss

## Description
This program takes in raw sentences and add monotonicity information to every constituent.

For example:

- input sentence: No man who likes every dog sleeps. 

- output: No&uarr; man&darr; who&darr; likes&darr; every&darr; dog&uarr; sleeps&darr; .&uarr;

- visualized output:

![image](example.png)

## Preparation
You need several things to run our program.

0. Clone this repository to your computer. Have Python 3.5 installed. Install the `beautifulsoup4` python package; you can do `pip3 install beautifulsoup4` or `conda install beautifulsoup4` if you use anaconda. 

1. Install C&C parser. 
All you need is download the precompiled binaries and the models 
(models trained on CCGbank 02-21 and MUC 7, 50MB) from the [webpage](http://www.cl.cam.ac.uk/~sc609/candc-1.00.html). 

2. Install easyCCG parser. You can simply clone [easyCCG](https://github.com/mikelewis0/easyccg) to your machine. 

3. Install ccg2lambda system. You can simply clone [ccg2lambda](https://github.com/mynlp/ccg2lambda) 
to your machine. 

4. Install some more python packages (for visualizing trees in ccg2lambda) by 
typing `pip3 install lxml simplejson pyyaml`.

5. Modify two scripts in ccg2lambda system. Simply copy the two python scripts in *files_for_ccg2lambda* to the folder *$ccg2lambda/scripts/* and replace the original files, where *$ccg2lambda* is the directory where you cloned ccg2lambda from step 3. This is to enable visualization of the arrows used in this project. 
   
6. Finally copy the paths of the above three programs (the CandC binaries and models, easyccg, and ccg2lambda) to *src/parse.sh* lines 27-31.

Then you are ready to go. 

## Polarize

*src/parse.sh* is a shell script that does parsing, polarizing all together. 

```bash
./parse.sh sentences.txt parser
```

where parser can be: `candc` or `easyccg`.

Depending on the parser you selected,  you will either see
`sentences.txt.candc_pretty.html` or `sentences.txt.easyccg_pretty.html`, which is the polarized 
output shown in the image above. 

## Algorithm

Our algorithm is described in this [paper](https://www.aclweb.org/anthology/S18-2015.pdf).

## infer (deprecated; will be uploaded to another repository)
*infer.py* first reads in 3 knowledge representations from the folder k:

- pairs.txt: dog < animal, beat < touch, etc.
- subsecAdj.txt: subsective adjectives such as good, bad, tall, etc.
- sentences4k.txt: sentences with "isA" relations such as "John is a cat."

It will then build a knowledge base on the above information (see our second paper
 below for details).
 
Finally, it will do inference using simple substitution, or replacement. 
Thus if the input sentence is "every&uarr; cat&darr; likes&uarr; some&uarr; good&uarr; dog&uarr;",
one replacement will result in inferences such as:

- every&uarr; cat&darr; likes&uarr; some&uarr; good&uarr; animal&uarr;
- every&uarr; cat&darr; likes&uarr; some&uarr; dog&uarr;

two replacements will result in:

- every&uarr; cat&darr; likes&uarr; some&uarr; animal&uarr; 

## TODO
[done] Add visualization to the final monotonicity output.

Handle more cases in inference.

## Cite
```
@inproceedings{hu-moss-2018-polarity,
    title = "Polarity Computations in Flexible Categorial Grammar",
    author = "Hu, Hai and Moss, Lawrence S.",
    booktitle = "Proceedings of the Seventh Joint Conference on Lexical and Computational Semantics",
    month = jun,
    year = "2018",
    address = "New Orleans, Louisiana",
    publisher = "Association for Computational Linguistics",
    url = "https://www.aclweb.org/anthology/S18-2015",
    doi = "10.18653/v1/S18-2015",
    pages = "124--129"
}
```

Or this which has a description of how _inference_ work in our system:
 
```
@inproceedings{monalog,
	title={\textbf{{MonaLog}: a Lightweight System for Natural Language Inference Based on Monotonicity}},
	author={\textbf{Hu, Hai} and Chen, Qi and Richardson, Kyle and Mukherjee, Atreyee and Moss, Lawrence S and Kuebler, Sandra},
	booktitle={Proceedings of the Society for Computation in Linguistics 2020},
	year={2020}
}
```

