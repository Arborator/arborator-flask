#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import json
import sys
import argparse
import collections, re
#debug=False
debug=True


"""

Bonjour, le script est lançable par la commande suivante :

python [CHEMIN_FICHIERS_CONLL] [CHEMIN_FICHIER_DE_SORTIE_JSON] -t [TRAIT] -t [GLOSSÒ]

Le script peut travailler sur plusieurs échantillons, 
mettez leurs noms les uns après les autres en les séparant par un espace. 
/!\ Si le chemin contient un espace, cela peut empêcher l'exécution du script. /!\ 

Chaque trait est précédé d'un symbole '-t'. 
Si un trait est déclaré, le script cherche seulement ce dernier. 
Par exemple, '-t Mood' nous donnera le résultat dans lequel seul le trait 'Mood' se présente et pas les autres traits.
Aucune déclaration de traits permettra au programme de traiter tous les traits morpho-syntaxiques existant dans le corpus.
La glose est optionnelle.

Voici un exemple de la commande:
python treebank2lexicon.py SUD_Naija-NSC-master/ABJ_GWA_02_Market-Food-Church_DG.conllu SUD_Naija-NSC-master/ABJ_GWA_03_Cost-Of-Living-In-Abuja_MG.conllu SUD_Naija-NSC-master/ABJ_GWA_06_Ugo-Lifestory_MG.conllu sortie.json -t PronType -t Mood -t Gloss

"""

class Tree(dict):
	"""
	just a dictionary that maps nodenumber->{"t":"qsdf", ...}
	moreover: 
		sentencefeatures is a dictionary with sentence wide information, eg "comments":"comment line content"
			there is a special key: _comments used for comments that are not of the form x = yyy, they are stored as such
		words is not necessarily a list of tokens: it contains the actual correctly spelled words, ie. the hyphen (1-2) lines
	"""
	def __init__(self, *args, **kwargs):
		self.update(*args, **kwargs)
		self.sentencefeatures={}
		self.words=[]

	def __getitem__(self, key):
		val = dict.__getitem__(self, key)
		#print 'GET', key
		return val

	def __setitem__(self, key, val):
		#print 'SET', key, val
		dict.__setitem__(self, key, val)

	def __repr__(self):
		#dictrepr = dict.__repr__(self)
		#return '%s(%s)' % (type(self).__name__, dictrepr)
		return self.conllu()
		#return "\n".join(["Tree: "+self.sentence()]+[f+": "+v for f,v in self.sentencefeatures.items()]+[str(i)+": "+self[i].get("t","")+"\t"+str(self[i]) for i in self])
	
	def update(self, *args, **kwargs):
		#print 'update', args, kwargs
		for k, v in dict(*args, **kwargs).items():
			self[k] = v
	
	def sentence(self):
		if self.words==[]:
			self.words = [self[i].get("t","") for i in sorted(self)]
		return " ".join(self.words)
	
	def conllu(self):
		morphoSynt= ['Abbr', 'AbsErgDatNumber', 'AbsErgDatPerson', 'AbsErgDatPolite', 'AdpType', 'AdvType', 'Animacy', 'Aspect', 'Case', 'Clusivity', 'ConjType', 'Definite', 'Degree', 'Echo', 'ErgDatGender', 'Evident', 'Foreign', 'Gender', 'Hyph', 'Mood', 'NameType', 'NounClass', 'NounType', 'NumForm', 'NumType', 'NumValue', 'Number', 'PartType', 'Person', 'Polarity', 'Polite', 'Poss', 'PossGender', 'PossNumber', 'PossPerson', 'PossedNumber', 'Prefix', 'PrepCase', 'PronType', 'PunctSide', 'PunctType', 'Reflex', 'Style', 'Subcat', 'Tense', 'Typo', 'VerbForm', 'VerbType', 'Voice']
		specialFeatures=["t", "lemma", "tag", "tag2", "xpos", "egov", "id", "index", "gov", "kids", "govrel", "span"]
		treestring = ""
		for stftkey in sorted(self.sentencefeatures):
			if stftkey=="_comments":
				if self.sentencefeatures[stftkey].endswith("#"): self.sentencefeatures[stftkey]=self.sentencefeatures[stftkey][:-1]
				treestring+="# "+self.sentencefeatures[stftkey]
			else:
				treestring+="# "+stftkey+" = "+self.sentencefeatures[stftkey]+"\n"	
		for i in sorted(self):
			node = self[i]                        
			govs=node.get("gov",{})
			govk = sorted(govs)
			if govk:
				gk,gv = str(govk[0]),govs.get(govk[0],"_")
			else:
				gk,gv = "_","_"
			treestring+="\t".join([
				str(i), 
				node.get("t","_"), 
				node.get("lemma",""), 
				node.get("tag","_"), 
				node.get("xpos","_"), 
				"|".join( [ a+"="+v for a,v in sorted(node.items()) if a in morphoSynt]) or "_", 
				gk,
				gv,
				"|".join( [ str(g)+":"+govs.get(g,"_") for g in govk[1:] ] + [ str(a)+":"+v for a,v in node.get("egov",{}).items() ] ) or "_", 
				"|".join( [ a+"="+v for a,v in sorted(node.items()) if a not in morphoSynt+specialFeatures])  or "_" 
				])+ "\n"
				
		return treestring
	
	def addkids(self, exclude=[]):
		"""
		adds dictionary to each node: 'kids': {1: 'dobj', 2: 'aux', 3: 'nsubj', 5: 'prep', 9: 'punct'}
		adds self.rootnode
		"""
		for i in self:
			self[i]['kids'] = {}
		for i in self:
			for g,f in self[i].get("gov",{}).items():
				if f in exclude: continue
				if g>0: self[g]["kids"][i]=f
				else: self.rootnode=i
					
				
	def addspan(self, exclude=[]):
		"""
		adds the list of direct and indirect dependents to each node
		needs that kids have been added first
		"""
		self.addkids(exclude)
		for i in self:
			self[i]['span'] = sorted(self.span(i))
			
	def span(self, i):
		"""
		recursive function going down the tree
		"""
		sp = [i]
		for j in self[i]['kids']:
			sp += self.span(j)
		return sp
	
	def addflux(self):
		flux = {}
		for i in self:
			for g,f in self[i].get("gov",{}).items():
				#if f in exclude: continue
				if g>0: 
					#print(i,g)
					for ii in range(min(i,g),max(i,g)):
						#print(ii)
						flux[ii]=flux.get(ii,0)+1
					#self[g]["kids"][i]=f
		self.flux=[f for i,f in sorted(flux.items())]

	def correctNumbering(self):
		"""
		if numbering is not consistent, not 1,2,3, ... this function corrects this
		"""
		indexcorrection = {0:0} # old index --> new index
		problem = False
		for c, ind in enumerate(sorted(self.keys())):
			indexcorrection[ind]=c+1
			if c+1 != ind:
				problem = True
		if problem:
			correctTree = Tree()
			for i, node in list(self.items()):
				node["id"]=indexcorrection[i]
				newgov={}
				for gi,f in node["gov"].items():
					newgov[indexcorrection[gi]]=f
				node["gov"]=newgov
				correctTree[indexcorrection[i]]=node
				del self[i]
			for i, node in correctTree.items():
				self[i]=correctTree[i]

	def replaceNodes(self, idsequence, headid, instree):
		"""
		idsequence: ids to be replaced
		headid: headid has to be in idsequence, dangling links are attached here
		instree: treestructure to be inserted. can be dict, list or string
		"""
		if isinstance(instree, str):instree = {i+1:{'t':t} for (i,t) in enumerate(instree.split())}
		elif isinstance(instree, list):instree = {i+1:{'t':t} for (i,t) in enumerate(instree)}
		
		insinds = sorted(instree.keys())
		id2newid = {0:0}
		for ind in sorted(self.keys()):
			if ind<idsequence[0]: id2newid[ind]=ind # before insertion
			elif ind in idsequence: # the nodes to be replaced
				if idsequence.index(ind) < len(instree): # align as long as possible
					id2newid[ind]=ind
				else: # spurious ones point to the headid
					id2newid[ind]=headid
			else: #behind insertion
				id2newid[ind]=ind+len(instree)-len(idsequence);		
		newtree = {}
		for ind in sorted(self.keys()):
			# spurious nodes just get kicked out (more elements to be kicked out than to be inserted):
			if ind in idsequence and idsequence.index(ind) >= len(instree): continue
			node = self[ind]
			node['id']=id2newid[ind]
			for gg in ['gov','egov']:
				newgov={}
				for gi,gf in node[gg].items(): newgov[id2newid[gi]]=gf
				node[gg]=newgov
			if ind in idsequence: # now i got to insert the matching nodes
				insnode = instree[insinds[idsequence.index(ind)]]
				for gg in ['gov','egov']:
					nngov = {}
					for gi,gf in insnode.get(gg,{}).items(): # just in case the instree contains govs
						if gi in instree: # not touching root relations and no outgoing relations
							nngov[gi+idsequence[0]-1]=gf
					if nngov: insnode[gg]=nngov
					elif gg in insnode: del insnode[gg]
				if 'id' in insnode: del insnode['id']
				node = {**node, **insnode}
			newtree[id2newid[ind]]=node
		for i in insinds[len(idsequence):]:
			insnode = instree[i]
			for gg in ['gov','egov']:
				nngov = {}
				for gi,gf in insnode.get(gg,{}).items(): # just in case the instree contains govs
					if gi in instree: # not touching root relations and no outgoing relations
						nngov[gi+idsequence[0]-1]=gf
				if nngov: insnode[gg]=nngov
				elif gg in insnode: del insnode[gg]
			newtree[i+idsequence[0]-1]=insnode
		sf = self.sentencefeatures
		self.__init__(newtree)
		sf['text'] = self.sentence()
		self.sentencefeatures = sf

	

def update(d, u):
	for k, v in u.items():
		if isinstance(v, collections.Mapping):
			r = update(d.get(k, {}), v)
			d[k] = r
		else:
			d[k] = u[k]
	return d


def conll2tree(conllstring):
	""" 
	takes the conll string (or malt) representation of a single tree and creates a Tree (dictionary) for it
	"""
	tree=Tree()
	nr=1
	skipuntil=0 # only used to get the right "words" sequence, doesn't touch the actual tokens
	for line in conllstring.split('\n'):
		#print line
		if line.strip():
			if line.strip().endswith('# sent_id = D_ENU_13_School-life_1'):
				line=line[1:]
			if line.strip()[0]=="#": # comment of conllu
				if "=" in line:
					tree.sentencefeatures[line.split("=")[0].strip()[1:].strip()]="=".join(line.split("=")[1:]).strip()
				else:
					tree.sentencefeatures["_comments"]=tree.sentencefeatures.get("_comments","")+line.strip()[1:]+"\n#"
				continue
			
			cells = line.split('\t')
			nrCells = len(cells)
			
			if nrCells in [4,10,14]:
				
				if nrCells == 4: # malt!
					t, tag, govid, rel = cells
					if govid=="_": govid=-1
					else:govid = int(govid)
					newf={'id':nr,'t': t, 'tag': tag,'gov':{govid: rel}}
					tree[nr]=update(tree.get(nr,{}), newf)
					nr+=1

				elif nrCells == 10: # standard conll 10 or conllu
					nr, t, lemma , tag, xpos, features, govid, rel, edeps, misc = cells
					if "-" in nr: 
						try:	skipuntil=int(nr.split("-")[-1])
						except:	skipuntil=float(nr.split("-")[-1])
						tree.words+=[t]
						continue
					try:	nr = int(nr)
					except:	nr = float(nr) # handling the 3.1 format for "emtpy nodes"
					if govid.strip()=="_": govid=-1
					else:
						try:	govid = int(govid)
						except:	
							try:	govid = float(govid)
							except: 
								try:	assert(govid[0]=='$') # for transconll
								except: raise FormatError("not number or variable: "+govid)
					egov={}
					if ":" in edeps: # the enhanced graph is used
						egov=dict([(gf.split(":")[0],gf.split(":")[-1]) for gf in edeps.split("|")])					
					
					newf={'id':nr,'t': t,'lemma': lemma, 'tag': tag, 'xpos': xpos, 'gov':{govid: rel}, 'egov':egov, 'misc': misc}
					if "=" in features:
						mf=dict([(av.split("=")[0],av.split("=")[-1]) for av in features.split("|")])
						newf=update(mf,newf)
					if "=" in misc:
						mf=dict([(av.split("=")[0],av.split("=")[-1]) for av in misc.split("|")])
						newf=update(mf,newf)
						del newf['misc']
					elif misc=="_":
						del newf['misc']
					tree[nr]=update(tree.get(nr,{}), newf)
					
					# to be removed:
					#if 'Glose' in tree[nr]: 
						#tree[nr]['Gloss']=tree[nr]['Glose']
						#del tree[nr]['Glose']
					#if 'startali' in tree[nr]: 
						#tree[nr]['AlignBegin']=tree[nr]['startali']
						#del tree[nr]['startali']
					#if 'endali' in tree[nr]: 
						#tree[nr]['AlignEnd']=tree[nr]['endali']
						#del tree[nr]['endali']
					# end to be removed
					
					if nr>skipuntil: tree.words+=[t]
					
				elif nrCells == 14:
					#mate:
					#6, inscriptions, _, inscription, _, N, _, pl|masc, -1, 4, _, dep, _, _
					nr, t, lemma, lemma2, tag, xpos, morph, morph2, govid, govid2, rel, rel2, _, _ = cells
					nr = int(nr)
					if govid.strip()=="_": govid=-1
					else:govid = int(govid)
					if govid2.strip()=="_": govid2=-1
					else:govid2 = int(govid2)
					if lemma=="_" and lemma2!="_":lemma=lemma2
					if tag=="_" and xpos!="_":tag=xpos
					if morph=="_" and morph2!="_":morph=morph2
					if rel=="_" and rel2!="_":
						rel=rel2
						govid=govid2
					newf={'id':nr,'t': t,'lemma': lemma,'lemma2': lemma2, 'tag': tag, 'xpos': xpos, 'morph': morph, 'morph2': morph2, 'gov':{govid: rel}, 'egov':{govid2: rel2} }
					
					
					
					tree[nr]=update(tree.get(nr,{}), newf)
					
					
			elif debug:
				print("strange conll:",nrCells,"columns!",line)
				print(ord(line[0]))
				print(line[0].encode('utf-8'))
				print(line[1])
	
	return tree

def get_lexicon(trees,dic, glose) :
	compteur=1
	sauf=["AlignBegin","AlignEnd" ,"Gloss","levenshtein", "MotNouveau", "aSupprimer", "Lang"] 	
	for bloc in trees :
		# print("-----")
		for num in bloc :
			# print(bloc[num],"++++++++++")
			trait=[]
			for key in list(bloc[num].keys()):
				if key == 'id' :
					break
				elif key not in sauf :
					# print(bloc[num][key], key)
					trait.append(key+"="+bloc[num][key])
			if trait :
				token = (bloc[num]['t'], bloc[num]['lemma'], "|".join(trait), bloc[num]['tag'],bloc[num]['Gloss'])
			else :
				token = (bloc[num]['t'], bloc[num]['lemma'], "_", bloc[num]['tag'],bloc[num]['Gloss'])
			if token in dic :
				dic[token]=dic[token]+1
			else :
				dic[token]=compteur
	return dic

def get_json(dic, out_path, glose, trait) :
	f = open(out_path, "w", encoding="utf-8")
	comp = 0
	if glose :
		trait.remove(["Gloss"])
		if trait :
			for key in dic :
				# print(key)
				#print(key[0], key[1], key[2], key[3], key[4]) #forme, lemme, traits, pos, glose
				features=[]
				for i in key[2].split("|") :
					for s in trait :
						if s[0] in i :
							features.append(i)
				if len(features)==0 :
					features="_"
				x = {
				"form" : key[0],
				"lemma" : key[1],
				"POS" : key[3],
				"features" : "|".join(features),
				"gloss" : key[4],
				"frequency" : dic[key]
				}
				f.write(json.dumps(x, indent=1))
				comp +=1
				if comp != len(dic) :
					f.write(",\n")
		else :
			for key in dic :
				x = {
				"form" : key[0],
				"lemma" : key[1],
				"POS" : key[3],
				"features" : key[2],
				"gloss" : key[4],
				"frequency" : dic[key]
				}
				f.write(json.dumps(x, indent=1))
				comp +=1
				if comp != len(dic) :
					f.write(",\n")
	else :
		if trait :
			for key in dic :
				# print(key)
				#print(key[0], key[1], key[2], key[3], key[4]) #forme, lemme, traits, pos, glose
				features=[]
				# print(trait)
				for i in key[2].split("|") :
					for s in trait :
						if s[0] in i :							
							features.append(i)
				if len(features)==0 :
					features="_"
				x = {
				"form" : key[0],
				"lemma" : key[1],
				"POS" : key[3],
				"features" : "|".join(features),
				"frequency" : dic[key]
				}
				f.write(json.dumps(x, indent=1))
				comp +=1
				if comp != len(dic) :
					f.write(",\n")

		else :
			for key in dic :
				x = {
				"form" : key[0],
				"lemma" : key[1],
				"POS" : key[3],
				"features" : key[2],
				"frequency" : dic[key]
				}
				f.write(json.dumps(x, indent=1))
				comp +=1
				if comp != len(dic) :
					f.write(",\n")

def conllFile2trees(path):
	"""
	file with path -> list of trees
	
	important function!	
	called from enterConll, treebankfiles, and uploadConll in treebankfiles.cgi
	
	"""
	trees=[]
	with open(path,"r") as f:
		conlltext=""
		for li in f:
			li=li.strip()
			if li: 	conlltext+=li+"\n"
			elif conlltext: # emptyline, sentence is finished
				tree=conll2tree(conlltext)
				trees+=[tree]
				del tree
				conlltext=""
		f.close()
		if conlltext.strip(): # last tree may not be followed by empty line
			tree=conll2tree(conlltext)
			trees+=[tree]
		return trees

def conllFile2lexicon(corpus_path, trait):
	"""
	file with path -> list of trees
	
	important function!	
	called from enterConll, treebankfiles, and uploadConll in treebankfiles.cgi
	
	"""
	# print(corpus_path)
	out_path=corpus_path.pop()
	dict_lexicon={}
	trees =[]
	glose = True
	if trait is not None :
		if ["Gloss"] not in trait:
			glose=False   
	elif trait is None :
		glose = False
	for fichier in corpus_path :
		trees+=conllFile2trees(fichier)
	
	temp = get_lexicon(trees,dict_lexicon, glose)
	for key, value in temp.items() :
		if key not in dict_lexicon :
			dict_lexicon[key] = value
	get_json(dict_lexicon, out_path, glose, trait)
	# print(trait)




def main_entry_point(argv=None):
	if argv is None:
		argv = sys.argv[1:]
	if argv:
		parser = argparse.ArgumentParser(
			description="Extraction du lexique et Transformation du lexique en json"
		)
		parser.add_argument(
			"corpus_path",
			metavar="fichier_conll",
			type=str,
			nargs="*",
			help="Le fichier en entrée",
		)

		parser.add_argument(
			"-t",
			metavar="trait",
			action="append",
			nargs="+",
			type=str,
			default=None,
			help="La liste des traits",
		)

		args = parser.parse_args(argv)
		return conllFile2lexicon(
			args.corpus_path,
			args.t
		)
	

# get_json(get_lexique("../SUD_Naija-NSC-master"))
# print(conllFile2lexicon("../SUD_Naija-NSC-master/ABJ_GWA_02_Market-Food-Church_DG.conllu"))

if __name__ == "__main__":
	sys.exit(main_entry_point(sys.argv[1:]))
