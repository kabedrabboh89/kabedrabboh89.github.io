import numpy as np
import pandas as pd
import cvxpy as cp
from time import time
start = time()


###  initialisation  ###
consumption = pd.read_csv('./data/consumption_data.csv')
der = pd.read_csv('./data/der.csv')


####  grid  ####

grid_price = consumption['price_grid']
grid_emf = consumption['emf_grid']

WT_gen = consumption['wind']

#####  parameters  #####
re_emf = 13.7

price_RE = 0.98
price_EV = 1
eta_inv = 0.98

capacity = 27
power = 10
eta_c = 0.9487
eta_d = 0.9487

soc_init = 0.2
soc_max = 0.9

####  optimization  ####

charging_RE = cp.Variable(24, nonneg=True)
charging_grid = cp.Variable(24, nonneg=True)
discharging = cp.Variable(24, nonneg=True)

def soc(i):
    soc = soc_init
    for t in range(i+1):
        soc += (eta_c * eta_inv *(charging_RE[t] + charging_grid[t]) - discharging[t]/(eta_inv * eta_d))/capacity
    return soc

constraints = []


for i in range(24):
    constraints += [charging_RE[i] <= WT_gen[i]]
    constraints += [(eta_inv*(charging_grid[i]+charging_RE[i])) <= power]
    constraints += [(discharging[i]/eta_inv) <= power]
    constraints += [soc(i) >= soc_init, soc(i) <= soc_max]


cost = 0
for i in range(24):
    cost += charging_grid[i] * grid_price[i]


revenue = 0
for i in range(24):
    revenue += (WT_gen[i]-charging_RE[i]) * price_RE * grid_price[i] \
               + discharging[i] * price_EV * grid_price[i]


objective = cp.Maximize(revenue-cost)
prob = cp.Problem(objective, constraints)
print(prob.solve(solver=cp.GUROBI, reoptimize=True, verbose=True))
#print(prob.solve(solver=cp.CVXOPT, max_iters=10000, reltol=1e-6, abstol=1e-6, feastol=1e-6, verbose=False))
#print(action.value)

RE_emf = np.zeros(24)
discharging_emf = np.zeros(24)
charging_emf = np.zeros(24)
total_emf = 0
total_discharging = 0

for i in range(24):
    RE_emf[i] = re_emf
    charging_emf[i] = charging_grid.value[i] * grid_emf[i] + charging_RE.value[i] * RE_emf[i]
    total_emf += charging_emf[i]
    total_discharging += discharging.value[i]

avg_emf = total_emf / total_discharging
RE_cap = np.zeros(24)
RE_price = price_RE * grid_price
BESS_price = price_EV * grid_price
for i in range(24):
    discharging_emf[i] = avg_emf
    RE_cap[i] = WT_gen[i] - charging_RE.value[i]
    if RE_cap[i] < 0.001:
        RE_price[i] = 10
    if discharging.value[i] < 0.001:
        BESS_price[i]= 10


results = {'RE_cap': RE_cap, 'RE_price': RE_price, 'emf_re': RE_emf, 'discharging': discharging.value,
           'BESS_price': BESS_price, 'emf_bess': discharging_emf, 'charging_RE': charging_RE.value,
           'charging_grid': charging_grid.value, 'price': grid_price, 'emf_grid': grid_emf}

df = pd.DataFrame.from_dict(results)
df.to_csv('./DER2results.csv', index=False, header=True)
print(f'time: {time() - start} seconds')


