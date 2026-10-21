import csv, math, random
random.seed(42)
price=100.0
with open('data/bars.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['timestamp','close'])
    for i in range(10000):
        price*=math.exp(random.gauss(0,0.001))
        w.writerow([1700000040000+i*60000,price])
