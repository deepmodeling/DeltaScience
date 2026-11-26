#!/usr/bin/env python3
"""Deterministic preparation from downloaded PDB and CCD files. No docking."""
from pathlib import Path
from collections import defaultdict
import json, hashlib, math, sys
import numpy as np
import gemmi
from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors, rdMolDescriptors

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "regenerated"
OUT.mkdir(parents=True, exist_ok=True)

def atom(line):
    return {'name':line[12:16].strip(),'res':line[17:20].strip(),
            'chain':line[21], 'num':int(line[22:26]),'ins':line[26],
            'xyz':np.array([float(line[i:i+8]) for i in (30,38,46)]),
            'el':line[76:78].strip().title(), 'line':line, 'alt':line[16]}

def selected(pdb, record, chain, residue=None, alt='A'):
    lines = (RAW/f'{pdb}.pdb').read_text().splitlines()
    result=[]
    for line in lines:
        if line[:6].strip()!=record or line[21]!=chain: continue
        a=atom(line)
        if a['el'] in ('H','D'): continue
        if residue is not None and a['res'] != residue: continue
        if a['alt'] not in (' ',alt): continue
        a['line']=line[:16]+' '+line[17:]
        result.append(a)
    assert len({(a['chain'],a['num'],a['ins'],a['name']) for a in result})==len(result)
    return result

def ligand(pdb, ccd, chain, filename, alt='A'):
    obs=selected(pdb,'HETATM',chain,ccd,alt)
    assert len({a['num'] for a in obs})==1
    block=gemmi.cif.read_file(str(RAW/f'{ccd}.cif')).sole_block()
    table=block.find(['_chem_comp_atom.atom_id','_chem_comp_atom.type_symbol','_chem_comp_atom.charge'])
    specs={row[0]:(row[1],int(row[2])) for row in table if row[1] not in ('H','D')}
    assert set(specs)=={a['name'] for a in obs}, (pdb,set(specs)-{a['name'] for a in obs})
    rw=Chem.RWMol(); idx={}
    for a in obs:
        element,charge=specs[a['name']]
        z=Chem.Atom(element.title()); z.SetFormalCharge(charge); z.SetProp('pdb_atom_name',a['name'])
        idx[a['name']]=rw.AddAtom(z)
    types={'SING':Chem.BondType.SINGLE,'DOUB':Chem.BondType.DOUBLE,'TRIP':Chem.BondType.TRIPLE,'AROM':Chem.BondType.AROMATIC}
    for row in block.find(['_chem_comp_bond.atom_id_1','_chem_comp_bond.atom_id_2','_chem_comp_bond.value_order']):
        if row[0] in idx and row[1] in idx: rw.AddBond(idx[row[0]],idx[row[1]],types[row[2]])
    mol=rw.GetMol(); Chem.SanitizeMol(mol)
    conf=Chem.Conformer(len(obs)); conf.Set3D(True)
    for i,a in enumerate(obs): conf.SetAtomPosition(i,a['xyz'])
    mol.AddConformer(conf)
    Chem.AssignStereochemistryFrom3D(mol)
    mol.SetProp('_Name',f'{ccd}: experimental {pdb} chain {chain} residue {obs[0]["num"]} altloc {alt if any(a["alt"]!=" " for a in obs) else "blank"}')
    mol.SetProp('SOURCE_PDB',pdb); mol.SetProp('CCD_ID',ccd); mol.SetProp('SOURCE_CHAIN',chain)
    mol.SetProp('SOURCE_RESIDUE',str(obs[0]['num'])); mol.SetProp('SOURCE_ALTLOC',alt if any(a['alt']!=' ' for a in obs) else 'blank')
    mol.SetProp('COORDINATE_TREATMENT','Deposited heavy atoms unchanged; CCD atom-name bond mapping; no optimization or docking')
    with Chem.SDWriter(str(OUT/filename)) as w: w.write(mol)
    template=Chem.SDMolSupplier(str(RAW/f'{ccd}_ideal.sdf'),removeHs=True)[0]
    assert Chem.MolToInchiKey(template)==Chem.MolToInchiKey(mol),(pdb,Chem.MolToInchiKey(template),Chem.MolToInchiKey(mol))
    return mol,obs,{'pdb_id':pdb,'chain':chain,'residue_number':obs[0]['num'],'ccd_id':ccd,
                    'heavy_atoms':len(obs),'formula':rdMolDescriptors.CalcMolFormula(mol),
                    'molecular_weight':Descriptors.MolWt(mol),'canonical_isomeric_smiles':Chem.MolToSmiles(mol),
                    'inchikey':Chem.MolToInchiKey(mol),'altloc':mol.GetProp('SOURCE_ALTLOC'),'file':filename}

def frame(res):
    cb=res['CB']['xyz']; x=res['CA']['xyz']-cb; x/=np.linalg.norm(x)
    y=res['N']['xyz']-cb; y-=x*np.dot(x,y); y/=np.linalg.norm(y)
    return cb,np.stack([x,y,np.cross(x,y)],axis=1)

def repair_asp35(atoms):
    grouped=defaultdict(dict)
    for a in atoms: grouped[(a['num'],a['res'])][a['name']]=a
    recipient=grouped[(35,'ASP')]; root,axes=frame(recipient)
    missing=['CG','OD1','OD2']; assert not any(n in recipient for n in missing)
    env=[a for a in atoms if a['num']!=35]
    p=np.stack([a['xyz'] for a in env]); radii={'C':1.70,'N':1.55,'O':1.52,'S':1.80}
    er=np.array([radii[a['el']] for a in env]); added_r=np.array([1.70,1.52,1.52])
    ranked=[]
    for (num,res),donor in grouped.items():
        if res!='ASP' or not all(n in donor for n in ['N','CA','CB']+missing):continue
        dr,da=frame(donor)
        coords=np.stack([donor[n]['xyz']-dr for n in missing])@da
        for degrees in range(0,360,10):
            t=np.deg2rad(degrees); rot=np.array([[1,0,0],[0,np.cos(t),-np.sin(t)],[0,np.sin(t),np.cos(t)]])
            new=coords@rot.T@axes.T+root
            gaps=np.linalg.norm(new[:,None,:]-p[None,:,:],axis=2)-added_r[:,None]-er[None,:]
            penalty=float(np.square(np.minimum(gaps+0.4,0)).sum())
            ranked.append((penalty,-float(gaps.min()),num,degrees,new))
    best=min(ranked,key=lambda x:x[:4]); new=best[4]
    maxserial=max(int(a['line'][6:11]) for a in atoms)
    for i,(name,xyz) in enumerate(zip(missing,new),1):
        el='C' if name=='CG' else 'O'
        line=f'ATOM  {maxserial+i:5d} {name:>4s} ASP A  35    {xyz[0]:8.3f}{xyz[1]:8.3f}{xyz[2]:8.3f}  1.00 99.99          {el:>2s}  '
        atoms.append(atom(line))
    return {'residue':'ASP A35','added_atoms':missing,'method':'Graft observed same-structure ASP sidechain in N/CA/CB local frame; rotate about CA-CB in 10 degree steps; deterministic minimum heavy-atom overlap penalty; observed atoms unchanged',
            'donor_residue':f'ASP A{best[2]}','rotation_degrees':best[3],
            'environment_overlap_penalty':best[0],'minimum_added_environment_vdw_gap':-best[1],
            'added_coordinates':{n:[round(float(v),3) for v in xyz] for n,xyz in zip(missing,new)}}

def main():
    manifest={'preparation_scope':'No docking, score calibration, candidate search, coordinate minimization or native-backbone remodeling',
              'software':{'python':sys.version,'rdkit':rdBase.rdkitVersion,'gemmi':gemmi.__version__},'targets':{}}
    configs=[('bcl2','6O0K','LBM','venetoclax'),('bclxl','4QVX','3CQ','a1155463')]
    for target,pdb,ccd,name in configs:
        stem=f'{target}_{pdb.lower()}_chainA'
        refname=f'site_reference_{name}_{pdb.lower()}_chainA.sdf'
        mol,obs,lig=ligand(pdb,ccd,'A',refname)
        protein=selected(pdb,'ATOM','A'); observed_count=len(protein)
        fixes=[]
        if pdb=='6O0K': fixes.append(repair_asp35(protein))
        protein.sort(key=lambda a:(a['num'],a['ins'],int(a['line'][6:11])))
        protein_file=stem+'_protein.pdb'
        (OUT/protein_file).write_text('REMARK 900 PREPARED FROM '+pdb+' CHAIN A; SEE ASSET MANIFEST FOR CONSTRUCT AND REPAIR\n'+'\n'.join(a['line'] for a in protein)+'\nTER\nEND\n')
        ligpos=mol.GetConformer().GetPositions(); low=ligpos.min(axis=0); high=ligpos.max(axis=0)
        distances=np.linalg.norm(np.stack([a['xyz'] for a in protein])[:,None,:]-ligpos[None,:,:],axis=2)
        pocket=sorted({a['num'] for a,d in zip(protein,distances.min(axis=1)) if d<=4.5})
        pr={'pdb_id':pdb,'chain':'A','observed_heavy_atoms':observed_count,'prepared_heavy_atoms':len(protein),
            'protein_file':protein_file,'pdbqt_file':stem+'.pdbqt','site_reference_pose':lig,
            'pocket_selection':'All chain A protein residues with a heavy atom within 4.5 Angstrom of native reference heavy atoms',
            'pocket_residues':pocket,'repairs':fixes,
            'box_center':list(np.round((low+high)/2,3)),
            'box_size':list(np.round(np.maximum(high-low+10,32),3)),
            'box_rule':'Native ligand axis span + 10 Angstrom, with each dimension at least 32 Angstrom',
            'ligand_axis_span':list(np.round(high-low,3)),'protein_atom_count_preserved':len(protein)==observed_count+sum(len(x['added_atoms']) for x in fixes)}
        radii={'C':1.7,'N':1.55,'O':1.52,'S':1.8,'Cl':1.75,'F':1.47,'P':1.8}
        gaps=distances-np.array([radii[a['el']] for a in protein])[:,None]-np.array([radii[a.GetSymbol()] for a in mol.GetAtoms()])[None,:]
        pr['native_ligand_geometry_qc']={'minimum_heavy_atom_distance':float(distances.min()),'minimum_vdw_gap':float(gaps.min()),'max_protein_coordinate_change_angstrom':0.0,
            'minimum_distance_from_ASP35_observed_atoms_to_ligand':float(min(distances[i].min() for i,a in enumerate(protein) if a['num']==35)) if pdb=='6O0K' else None}
        manifest['targets'][target]=pr
    nav,navobs,navinfo=ligand('4LVT','1XJ','A','navitoclax_4lvt_chainA_experimental.sdf')
    manifest['shared_reference']=navinfo
    manifest['shared_reference']['coordinate_role']='Chemical identity and provenance only; 4LVT coordinates are not in either prepared receptor frame and must not be treated as a native pose for 6O0K or 4QVX.'
    manifest['sources']={p:{'url':f'https://files.rcsb.org/download/{p}.pdb','pdb_page':f'https://www.rcsb.org/structure/{p}'} for p in ['6O0K','4QVX','4LVT']}
    manifest['hashes']={'raw/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RAW.iterdir()) if p.is_file()}
    manifest['hashes'].update({'prepared/'+p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.suffix in {'.pdb','.sdf','.pdbqt'}})
    (OUT/'asset_manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    print(json.dumps(manifest['targets'],indent=2))
if __name__=='__main__': main()
