import numpy as np

s = np.array([11074.8, 11088.4,
              11145, 11160.3, 11174.3,
              11195.7,
              11237.5,
              11261.9, 11263.2,
              11289,
              11340.4,
              11366.2, 11369.2, 11369.2,
              11391.9,
              11425.7,
              11455.1, 11469.1, 11476.4,
              11542.7,
              11636.3, 11649.9, 11652])
ecrat = []
zone = []
list=[]
n0 = 0
n1 = 1
for l in s:
    print(l)
    if n0 == 0:
        n0=l
    else:
        n1 = l
        d = abs(round(n0 - n1, 2))

        if d < 16 :
            if len(ecrat) == 0:
                ecrat.append(n0)

            ecrat.append(n1)
            n0 = n1

        else:
            print("len(ecrat):",len(ecrat))
            if len(ecrat) > 0:
                list = ecrat.copy()
                print("insertion de zone")
                zone.append(list)
                ecrat.clear()
            else:
                zone.append([n0])
            n0 = n1


    print("ecrat :",ecrat)
    print("zone :",zone)
    print("n0:", n0)
    print("-----------------------------------")

if len(ecrat) > 0:
    list = ecrat.copy()
    print("insertion de zone")
    zone.append(list)
    ecrat.clear()
else:
    zone.append([n0])



print(zone)
print(11366.2 in zone)
i = np.where(zone == 11074.8)
print(i)