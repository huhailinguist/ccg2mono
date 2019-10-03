'''
test wordNet

POS tags:
ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'

Hai Hu, Feb 2018

TABLE:
young man <= man
dog <= animal
...

We only put the words in the premises, conclusion to the table
If we go over the table multiple times, we might end up adding
  'young' to 'man' multiple times!


'''

from nltk.corpus import wordnet as wn

def main():
    test()

def test():
    print(getHypernyms('man', pos=wn.NOUN))
    print(getHypernyms('man', pos=wn.VERB))
    print(getHypernyms('dog'))
    print(getHypernyms('cat'))
    print(getHypernyms('chair'))
    print(getHypernyms('army'))

def testWN():
    for ss in wn.synsets('man'):
        for hyper in ss.hypernyms():
            print(ss, hyper, hyper.name())

# ---------------------  recursively get all --------------------
def getAllHyps(hypType, word, pos=None):
    ''' get all hypernyms RECURSIVELY of the input word
        output: a list of strings (could be Synsets)
    '''
    hyps_synsets = set()
    for ss in wn.synsets(word):
        if pos:
            if ss.name().split('.')[1] == pos:
                hyps_synsets.update(getHypsHelper(ss, hypType))
    hyps_str = [x.name()[:x.name().find(r'.')] for x in hyps_synsets]
    return sorted(hyps_str)

def getHypsHelper(synset, hypType):
    hypsInHelper = set()
    if hypType.lower() == 'hypernym':
        for hypernym in synset.hypernyms():
            hypsInHelper |= set(getHypsHelper(hypernym, hypType))
        return hypsInHelper | set(synset.hypernyms())
    elif hypType.lower() == 'hyponym':
        for hyponym in synset.hyponyms():
            hypsInHelper |= set(getHypsHelper(hyponym, hypType))
        return hypsInHelper | set(synset.hyponyms())
    else:
        print('cannot find {} in wordnet!'.format(hypType))
# ---------------------  END: recursively get all --------------------

# ----------------------  ONE LEVEL ------------------------------
def getHypernyms(word, pos=None):
    ''' get all hypernyms ONE LEVEL UP of the input word
        output: a list of strings
        Synset: can.v.01
        pos can be: ADJ, ADJ_SAT, ADV, NOUN or VERB
    '''
    hypernyms = []
    for ss in wn.synsets(word):
        for hyper in ss.hypernyms():
            # could be: skilled_worker
            hyperpos = hyper.name().split('.')[1]
            if pos:
                if hyperpos == pos:
                    h = hyper.name()[:hyper.name().find(r'.')] #.replace('_', ' ')
                    hypernyms.append(h)
            else:
                h = hyper.name()[:hyper.name().find(r'.')] #.replace('_', ' ')
                hypernyms.append(h)
    return hypernyms

def getHyponyms(word, pos=None):
    ''' get all hyponyms ONE LEVEL DOWN of the input word
        output: a list of strings
        pos can be: ADJ, ADJ_SAT, ADV, NOUN or VERB
    '''
    hyponyms = []
    for ss in wn.synsets(word):
        for hypo in ss.hyponyms():
            # could be: skilled_worker
            hypopos = hypo.name().split('.')[1]
            if pos:
                if hypopos == pos:
                    h = hypo.name()[:hypo.name().find(r'.')] #.replace('_', ' ')
                    hyponyms.append(h)
            else:
                h = hypo.name()[:hypo.name().find(r'.')] #.replace('_', ' ')
                hyponyms.append(h)
    return hyponyms
# ----------------------  END: ONE LEVEL ------------------------------

if __name__ == '__main__':
    main()


'''
All hyponyms of 'man'

['adjutant', 'adjutant_general', 'admiral', 'adonis', 'air_force_officer', 'aircraftsman', 'anzac', 'armorer', 'army_officer', 'artilleryman', 'babu', 'bachelor', 'bey', 'bishop', 'black', 'black_and_tan', 'black_man', 'blucher', 'bluejacket', 'bombardier', 'boskop_man', 'boy', 'boy', 'boyfriend', 'brass_hat', 'brigadier', 'broth_of_a_boy', 'bull', 'bushwhacker', 'cannon_fodder', 'captain', 'captain', 'carbineer',
'casanova', 'castle', 'cavalryman', 'cavalryman', 'charge_of_quarters', 'checker', 'chessman', 'chief_of_staff', 'chief_petty_officer', 'coastguardsman', 'codger', 'colonel', 'color_bearer', 'color_sergeant', 'commander', 'commander_in_chief', 'commanding_officer', 'commando', 'commissioned_military_officer', 'commissioned_naval_officer', 'commissioned_officer', 'commodore', 'confederate_soldier', 'corporal', 'coxcomb', 'cro-magnon',
'cuirassier', 'dandy', 'desk_officer', 'dirty_old_man', 'don', 'don_juan', 'doughboy', 'draftee', 'dragoon', 'drill_master', 'ejaculator', 'enlisted_man', 'enlisted_person', 'enlisted_woman', 'ensign', 'esquire', 'eunuch', 'ex-boyfriend', 'ex-husband', 'executive_officer', 'father-figure', 'father_figure', 'fellow', 'field-grade_officer', 'field_marshal', 'first_lieutenant', 'first_sergeant', 'flag_captain', 'flag_officer', 'flanker',
'fleet_admiral', 'foster-father', 'fusilier', 'galoot', 'geezer', 'general', 'general_officer', 'gent', 'gentleman', 'gentleman-at-arms', 'goldbrick', 'good_old_boy', 'grass_widower', 'green_beret', 'grenadier', 'guardsman', 'gunnery_sergeant', 'gurkha', 'guy', 'herr', 'highlander', 'homo_erectus', 'homo_habilis', 'homo_sapiens', 'homo_sapiens_sapiens', 'homo_soloensis', 'hooray_henry', 'housefather', 'hunk', 'hussar', 'inamorato', 'infantryman',
'inspector_general', 'iron_man', 'ironside', 'janissary', 'java_man', 'jawan', 'judge_advocate', 'judge_advocate', 'judge_advocate_general', 'king', 'king', 'kitchen_police', 'knight', 'lance_corporal', 'lancer', 'legionnaire', 'legionnaire', 'lieutenant', 'lieutenant', 'lieutenant_colonel', 'lieutenant_commander', 'lieutenant_general', 'lieutenant_junior_grade', 'line_officer', 'lothario', 'macaroni', 'major', 'major-general', 'man-at-arms', 'marine',
'marine', 'marshal', 'master-at-arms', 'master_sergeant', 'middle-aged_man', 'military_adviser', 'military_officer', 'militiaman', 'minuteman', 'monsieur', 'musketeer', 'naval_commander', 'naval_officer', 'navy_seal', 'neandertal_man', 'noncombatant', 'noncommissioned_officer', 'occupier', 'old-timer', 'old_boy', 'old_man', 'one_of_the_boys', 'orderly', 'orderly_sergeant', 'paratrooper', 'patriarch', 'patriarch', 'pawn', 'peacekeeper',
'peking_man', 'peter_pan', 'petty_officer', 'pistoleer', 'poilu', 'point_man', 'ponce', 'posseman', 'potemkin', 'private', 'quartermaster', 'quartermaster_general', 'queen', 'ranker', 'ranker', 'raw_recruit', 'rear_admiral', 'rebel', 'recruit', 'recruiting-sergeant', 'redcoat', 'regular', 'reservist', 'rhodesian_man', 'rifleman', 'rough_rider', 'second_lieutenant', 'section_eight', 'senhor', 'senior_chief_petty_officer', 'senior_master_sergeant',
'sergeant', 'sergeant_major', 'shaver', 'signor', 'signore', 'sir', 'sod', 'soldier', 'solo_man', 'soul_brother', 'sprog', 'squaw_man', 'staff_officer', 'staff_sergeant', 'stepfather', 'stiff', 'striker', 'striper', 'stud', 'subaltern', 'sublieutenant', 'submariner', 'supply_officer', 'supreme_allied_commander_atlantic', 'supreme_allied_commander_europe', 'tanker', 'tarzan', 'technical_sergeant', 'territorial', 'tile', 'trainbandsman',
 'unknown_soldier', 'uriah', 'veteran', 'veteran', 'vice_admiral', 'volunteer', 'wac', 'warrant_officer', 'wave', 'weekend_warrior', 'white', 'white_man', 'widower', 'wing_commander', 'wolf', 'womanizer', 'wonder_boy', 'world', 'yard_bird', 'yellow_man', 'young_buck']


'''
