import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab
def frames(seed, total):
    random.seed(seed); B=["B","Y","X","A","L","R","UP","DOWN","LEFT","RIGHT"]
    sp=[["DOWN"],["RIGHT"],["Y"]],[["LEFT"],["LEFT"],["B"]],[["DOWN"],["LEFT"],["B"]]
    out=[]; n=0
    while n<total:
        if random.random()<0.3:
            for stp in random.choice(sp): out+=[(stp,random.sample(B,1))]*3+[([],[])]*3; n+=6
        else:
            k=random.randint(2,10); b1=random.sample(B,random.randint(0,3)); b2=random.sample(B,random.randint(0,3)); out+=[(b1,b2)]*k; n+=k
    return out
def crashed_at(rom, seed, total):
    c=lab.fight(os.path.abspath(rom))
    for i,(b1,b2) in enumerate(frames(seed,total)):
        c.run2(1,b1,b2)
        if i%30==0:
            c.watch_read(0xC00000,0xFFFFFF); c.run2(1,[],[]); lg=c.log(400000); c.reset_hooks()
            def bad(pc):
                b, a = (pc >> 16) & 0x7F, pc & 0xFFFF
                return b in (0x7E, 0x7F) or (b < 0x40 and a < 0x8000)
            if not lg or all(bad(e['pc']) for e in lg[-50:]): return i
    return None
if __name__=="__main__":
    for rom in sys.argv[2:]:
        print(rom, "seed", sys.argv[1], "crash at", crashed_at(rom, int(sys.argv[1]), 3000))
