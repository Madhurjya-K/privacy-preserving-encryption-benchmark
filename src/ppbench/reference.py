"""Independent plaintext oracle: no pipeline or crypto functions imported."""
import json
from decimal import Decimal,ROUND_HALF_EVEN

def reference(rows,numeric,group,scale=100):
    groups={}
    for row in rows:
        key='ALL' if group is None else json.dumps(row.get(group),sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
        if key not in groups:groups[key]={'count_star':0,'fields':{f:[0,0] for f in numeric}}
        item=groups[key];item['count_star']+=1
        for f in numeric:
            if row.get(f) is not None:
                item['fields'][f][0]+=int((Decimal(str(row[f]))*Decimal(scale)).quantize(Decimal(1),rounding=ROUND_HALF_EVEN))
                item['fields'][f][1]+=1
    result={}
    for key,item in groups.items():
        fields={}
        for f,(total,count) in item['fields'].items():
            total=Decimal(total)/Decimal(scale)
            fields[f]={'sum':None if not count else str(total),'count_nonnull':count,'avg':None if not count else str(total/Decimal(count))}
        result[key]={'count_star':item['count_star'],'fields':fields}
    return result
