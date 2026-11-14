#!/usr/bin/env python3
"""Reproduce numerical audit estimates. No CAD writes, network or external dependencies.
Usage: python3 calculations.py --verification verification.json --inventory inventory.json --out calculations.json
Efficiency values are assumptions, not measurements. Pad lengths are center-to-center bounds.
"""
import argparse,itertools,json,math
from pathlib import Path
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--verification',type=Path,required=True);ap.add_argument('--inventory',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
j=json.loads(args.verification.read_text());n=json.loads(args.inventory.read_text());pads=j['pads']
def dist(a,ap,b,bp):return min(math.dist(x['xy'],y['xy'])for x in pads[a][ap]for y in pads[b][bp])
result={'pad_center_distances':{},'converters':{},'thermal_assumptions':{},'trace_width_mm_IPC2221_external_35um_deltaT10C':{},'impedance_approximation':{}}
for u,caps,l,couts,rlo in [('U2',['C6','C7'],'L1',['C9','C10'],'R14'),('U3',['C12','C13'],'L2',['C15','C16'],'R19'),('U4',['C18','C19'],'L3',['C21','C22'],'R24'),('U5',['C26','C27'],'L4',['C30','C31','C32','C33'],'R31'),('U6',['C37','C38'],'L5',['C41','C42','C43','C44'],'R38')]:
    sw=next(pi for pi,d in n[u]['pins'].items()if d.get('function')=='SW');fb=next(pi for pi,d in n[u]['pins'].items()if d.get('function')=='FB');vi=[pi for pi,d in n[u]['pins'].items()if d['net']=='+24V_P']
    result['pad_center_distances'][u]={'VIN_to_cap_pad1_mm':{c:{pi:round(dist(u,pi,c,'1'),4)for pi in vi}for c in caps},'SW_to_L_pad1_mm':round(dist(u,sw,l,'1'),4),'L_pad2_to_COUT_pad1_mm':{c:round(dist(l,'2',c,'1'),4)for c in couts},'FB_to_low_resistor_pad1_mm':round(dist(u,fb,rlo,'1'),4)}
for u,vo,io,L,dcr in [('U2',12,1,10e-6,.0165),('U3',5,1,6.8e-6,.0115),('U4',3.3,1.2,4.7e-6,.04),('U5',5,5,6.8e-6,.0115),('U6',5,5,6.8e-6,.0115)]:
    freq=400e3 if u in ['U5','U6'] else 500e3
    ripple=vo*(1-vo/32)/(L*freq);ripple_corner=ripple/(.8*.9);irms=math.sqrt(io**2+ripple**2/12);pdc=irms**2*dcr
    result['converters'][u]={'Vout':vo,'Iout':io,'L_H':L,'fsw_Hz':freq,'ripple_A_at32V_nominal':ripple,'ripple_A_Lminus20_fminus10':ripple_corner,'peak_A_nominal':io+ripple/2,'peak_A_worst_L_f':io+ripple_corner/2,'Irms_A_nominal':irms,'P_DCR_max25C_W':pdc,'P_DCR_max100C_W':pdc*(1+.00393*75)}
for current in [6,5,3,1.2,1,.5]:
    area_mil2=(current/(.048*10**.44))**(1/.725);result['trace_width_mm_IPC2221_external_35um_deltaT10C'][str(current)]=area_mil2/(35/25.4)*.0254
for z in [100,90]:
    h=.2104;er=4.4;t=.035;gap=.2;z0=z/2/(1-.48*math.exp(-.96*gap/h));width=(5.98*h/math.exp(z0*math.sqrt(er+1.41)/87)-t)/.8
    result['impedance_approximation'][str(z)]={'stack':'JLC04161H-7628','h_mm':h,'er':er,'copper_mm':t,'gap_mm':gap,'width_mm':width,'limitations':'Homogeneous substrate model; no solder mask, etch taper or field solver.'}
for u,po,etas,theta in [('LM61460',25,[.90,.92],25),('LMR12',12,[.90,.94],80),('LMR5',5,[.88,.90],80),('LMR3v3',3.96,[.85,.88],80)]:
    rkey={'LM61460':'U5','LMR12':'U2','LMR5':'U3','LMR3v3':'U4'}[u];pl=result['converters'][rkey]['P_DCR_max100C_W'];scenarios=[]
    for eta in etas:
        loss_total=po*(1/eta-1);loss_ic_and_other=max(0,loss_total-pl);scenarios.append({'assumed_efficiency':eta,'P_converter_total_W':loss_total,'P_inductor_copper_W':pl,'P_IC_plus_other_external_loss_W':loss_ic_and_other,'assumed_theta_C_W':theta,'Tj_C_if_remaining_loss_all_at_IC_Ta70':70+theta*loss_ic_and_other,'required_theta_for_Tj125':55/loss_ic_and_other})
    result['thermal_assumptions'][u]={'note':'Efficiencies assumed. Subtracting DCR alone still leaves other external losses; IC heat not measured. Theta not a PCB guarantee.','scenarios':scenarios}
result['thermal_assumptions']['TPS26631']={'at_6A':{'P_R31mOhm_W':36*.031,'P_R53mOhm_W':36*.053,'Tj_at_70_theta32_2_Rmax':70+36*.053*32.2,'theta_required_Tj125':55/(36*.053)},'at_6_42A':{'P_R53mOhm_W':6.42**2*.053,'theta_required_Tj125':55/(6.42**2*.053)}}
result['thermal_assumptions']['RTL8305NB']={'P_all_ports_including_internal_LDO_W':.4125+(3.3-1.2)*.088,'Tj_C_at70_theta51_6':70+51.6*(.4125+(3.3-1.2)*.088),'note':'Typical room-temperature datasheet currents, not maximum hot currents.'}
uv=[];ov=[]
for aa,bb,cc,t,iv,iu in itertools.product([.99,1.01],[.99,1.01],[.99,1.01],[1.176,1.224],[-150e-9,150e-9],[-150e-9,150e-9]):
    A=390000*aa;B=19100*bb;C=15000*cc;ov.append(t*(1+(A+B)/C)+iv*(A+B)+iu*A);uv.append(t*(1+A/(B+C))+A*iv*C/(B+C)+A*iu)
result['efuse_thresholds_V']={'UVLO_nominal':1.2*424.1/34.1,'OVP_nominal':1.2*424.1/15,'UVLO_corner_minmax':[min(uv),max(uv)],'OVP_corner_minmax':[min(ov),max(ov)],'assumptions':'1% resistor tolerance, +/-2% threshold, +/-150nA independent input leakage.'}
result['via_R_ohm_25C_0_30mm_18um_1_6mm']=1.724e-8*.0016/(math.pi*.00030*.000018)
result['output_setpoints_V']={'U2':.6*(1+100/5.23),'U3':.6*(1+100/13.7),'U4':.6*(1+100/22.1),'U5_U6':1+100/24.9}
result['pca_default_typical']={'V_default':3.3*10/110,'pull_current_A':3.3/110000,'Rpu_min_to_meet_0_8V_ohm':10000*(3.3/.8-1),'note':'Internal 100k model lacks guaranteed tolerance.'}
args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(args.out)
