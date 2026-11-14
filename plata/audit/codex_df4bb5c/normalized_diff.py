# Run alongside audit_checks.py with the same --repo/--ci/--old-ci/--out arguments.
exec((__import__('pathlib').Path(__file__).with_name('audit_checks.py')).read_text().split('new=read(ci)')[0])
a=read(old);b=read(ci)
# Exact common electrical nodes; new diagnostic nodes are omitted from comparison.
excluded_refs={'F4','F5','Q5','Q6','Q7','Q8','Q9','R72','R73'}
excluded_pins={('J7','8'),('J7','SH'),('J18','8'),('J18','SH')}
common={(r,pin)for r,c in a.items()if r in b and r not in excluded_refs for pin,v in c['pins'].items()if pin in b[r]['pins']and not v['net'].startswith('unconnected-')and not b[r]['pins'][pin]['net'].startswith('unconnected-')}-excluded_pins
parent={}
def root(x):
 while x in parent:x=parent[x]
 return x
for r in ['F4','F5']:
 vals=list(a[r]['pins'].values());x,y=root(vals[0]['net']),root(vals[1]['net']);parent[x]=y

def partitions(cs,old=False):
 ns={}
 for r,pin in common:
  name=cs[r]['pins'][pin]['net'];name=root(name)if old else name;ns.setdefault(name,set()).add((r,pin))
 return {frozenset(s):name for name,s in ns.items()}
x,y=partitions(a,True),partitions(b);diff=[{'old_name':x.get(k),'new_name':y.get(k),'nodes':sorted(k)}for k in set(x)^set(y)]
res={'excluded_refs':sorted(excluded_refs),'excluded_pins':sorted(excluded_pins),'removed_fuses_contracted':['F4','F5'],'common_electrical_nodes_checked':len(common),'unexpected_topology_differences':diff,'renamed_nets':{x[k]:y[k]for k in x.keys()&y.keys()if x[k]!=y[k]}}
(result_dir/'normalized_net_diff.json').write_text(json.dumps(res,ensure_ascii=False,indent=2));print('common nodes',len(common),'unexpected partitions',len(diff),'renames',res['renamed_nets'])
