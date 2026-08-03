# Generates tools/phase6-bench.pd. Same shape as phase5-bench: self-driving,
# ten seconds a step, a printed PASS IF before every step INCLUDING the ones
# whose correct result is that nothing happens.
steps = [
 ("baseline -- 120 BPM -- stopped -- compose mode-1",
  "PASS IF: the top row shows ONE bright green lamp at the far left and five dim ones beside it -- and the BOTTOM row of pads has a single white pad. Everything else on the surface is dark",
  [("120","tempo"),("bang","stop"),("compose mode-1","mode")]),
 ("MODE -- selecting the fourth mode",
  "PASS IF: the bright lamp MOVES to the fourth position and the other five go dim. Nothing else on the grid changes",
  [("perform mode-4","mode")]),
 ("MODE -- the sixth and last lamp",
  "PASS IF: the bright lamp lands on the sixth and last position. ONE MESSAGE PER STEP FOR ANYTHING VISUAL: two sent back to back both land inside the same frame and only the second is ever drawn -- found by running this bench and watching the painted frames rather than the surface",
  [("perform mode-6","mode")]),
 ("MODAL -- the whole surface claimed",
  "PASS IF: EVERY pad and every lamp on the top row turns blue. The mode lamps are covered too -- that is the point of a modal. THE OLED MUST NOT CHANGE",
  [("grid modal 45","disp")]),
 ("MODE CHANGE UNDERNEATH A MODAL -- nothing should be visible",
  "PASS IF: NOTHING HAPPENS. The surface stays blue. The mode really does change underneath and you will see it two steps from now",
  [("perform mode-3","mode")]),
 ("MODAL OFF",
  "PASS IF: the grid returns to mode lamps and the beat row -- and the bright lamp is now the THIRD one -- which is the change made while the modal covered it",
  [("grid modal-off","disp")]),
 ("ALERT -- a fail -- which outranks everything",
  "PASS IF: the whole surface turns RED -- and then goes back to the mode lamps BY ITSELF after about two seconds. A grid that stays red is the bug this step exists for",
  [("fail u_bench boom","err")]),
 ("ALERT -- a warn -- which the grid must ignore",
  "PASS IF: NOTHING HAPPENS ON THE GRID. The OLED still shows the warning. Only a fail is worth the whole surface",
  [("warn u_bench quiet","err")]),
 ("TRANSPORT -- start",
  "PASS IF: the white pad WALKS along the bottom row -- twice a second -- and the aux button goes green. On the Mac with DSP off it will not move -- tick enable-DSP first",
  [("bang","start")]),
 ("TEMPO -- 240 BPM -- so the beat row should double",
  "PASS IF: the white pad moves twice as fast. The console prints BEATS for the ten seconds before this step and after it -- expect about 20 then about 40",
  [("240","tempo")]),
 ("back to 120 and stopped",
  "PASS IF: the beat row slows to two a second. THE CLOCK KEEPS RUNNING WHEN THE TRANSPORT STOPS -- so the pad must keep walking after the stop",
  [("120","tempo"),("bang","stop")]),
 ("HANDS ON THE LAUNCHPAD -- press pads and ring buttons",
  "PASS IF: every pad you press reports pad-NN on the OLED with its velocity -- and a ring button reports lp-cc-NN. Pressure on a held pad reports NOTHING on the OLED -- that is deliberate and it is not a fault",
  []),
 ("HANDS ON THE NANOKONTROL -- the six transport keys",
  "PASS IF: each of the six keys moves the bright lamp to its own position. This is the mode bus finally having a driver",
  []),
 ("PANIC -- the surface goes back to the device",
  "PASS IF: the Launchpad leaves Programmer Mode and its OWN display returns. The grid is no longer ours. KNOWN AND DELIBERATE: it stays that way until the patch is reloaded",
  [("bang","panic")]),
 ("HANDS -- press a pad now -- after the panic",
  "PASS IF: NOTHING REACHES THE OLED. In a stock layout the notes are musical pitches rather than r*10+c -- and decoding them as coordinates would publish nonsense. Reload the patch to get the grid back",
  []),
 ("done -- stop the patch",
  "PASS IF: nothing further prints. Reload with deploy.sh to restore normal operation",
  []),
]

B=[]                                   # boxes, in file order
C=[]                                   # connects
for _t,_p,_a in steps:
    for _s in (_t,_p):
        assert "," not in _s and ";" not in _s, "comma or semicolon in a message box: "+_s

def obj(x,y,s): B.append("#X obj %d %d %s;"%(x,y,s)); return len(B)-1
def msg(x,y,s): B.append("#X msg %d %d %s;"%(x,y,s)); return len(B)-1
def txt(x,y,s,f=110): B.append("#X text %d %d %s, f %d;"%(x,y,s,f)); return len(B)-1
def con(a,ao,b,bi): C.append("#X connect %d %d %d %d;"%(a,ao,b,bi))

txt(20,20,"phase6-bench -- the Phase 6 acceptance run: the Launchpad \\, the grid arbiter \\, the mode bus and the first c_clock instance. Ten seconds a step \\, so you can watch the surface and mark each one off. Load it as a THIRD patch after mother.pd and main.pd. It touches nothing in the deployed patch: it only pushes onto mode \\, disp \\, err \\, tempo \\, start \\, stop and panic \\, exactly as a controller would.")
txt(20,130,"RUN IN THE FOREGROUND AND WATCH THE LAUNCHPAD \\, not the screen. Every step prints what it is sending and a PASS IF line BEFORE the surface moves -- including the steps whose correct result is that NOTHING happens \\, which are otherwise impossible to mark off. Steps 12 \\, 13 and 15 need your hands: nothing but the real controllers can exercise notein and ctlin.")
txt(20,240,"NO COMMAS OR SEMICOLONS IN A PASS IF LINE. Both are message separators \\, so one comma splits the string and the remainder lands somewhere unhelpful. phase3-bench says so \\, phase4-bench was caught by it anyway \\, and this file is generated partly so that it cannot happen again.")
txt(20,350,"THE BEAT COUNTER BELOW is the one automated assertion here. Everything else about a grid is visual by nature -- there is no way to read back what the LEDs are actually showing \\, so this bench proves the cases it contains and nothing more. Two of Phase 5's worst bugs were invisible to a bench that passed.")

say=obj(4600,240,"print")
sayr=obj(4600,180,"r \\$0-say"); con(sayr,0,say,0)

# beat counter -- proves the clock is still running and following tempo
bc_r=obj(200,470,"r clock"); bc_t=obj(200,520,"t b"); bc_f=obj(200,570,"f")
bc_p=obj(340,620,"+ 1"); bc_s=obj(340,670,"t f f"); bc_h=obj(340,720,"f")
bc_z=obj(560,520,"r \\$0-zero"); bc_z2=msg(560,570,"0")
bc_rd=obj(200,720,"r \\$0-read"); bc_pr=obj(340,780,"print BEATS")
con(bc_r,0,bc_t,0); con(bc_t,0,bc_f,0); con(bc_f,0,bc_p,0); con(bc_p,0,bc_f,1)
con(bc_z,0,bc_z2,0); con(bc_z2,0,bc_f,1)
con(bc_rd,0,bc_h,0); con(bc_p,0,bc_h,1); con(bc_h,0,bc_pr,0)
txt(700,470,"Counts master beats. Zeroed and read by the tempo steps \\, so the two printed numbers are ten seconds at 120 BPM and ten at 240 -- about 20 and about 40. On the Mac with DSP OFF both read 0 \\, which looks exactly like a dead clock rather than a setting.",70)

lb=obj(20,900,"loadbang")
prev=obj(20,960,"del 6000"); con(lb,0,prev,0)

Y=1100
for i,(title,passif,actions) in enumerate(steps):
    n=len(actions)
    tr=obj(200,Y+40,"t "+" ".join(["b"]*(n+3)))
    con(prev,0,tr,0)
    tm=msg(500,Y+110,"=== STEP-%02d-of-%d === %s"%(i+1,len(steps),title))
    ts=obj(500,Y+170,"s \\$0-say"); con(tr,n+2,tm,0); con(tm,0,ts,0)
    pm=msg(500,Y+240,passif)
    ps=obj(500,Y+300,"s \\$0-say"); con(tr,n+1,pm,0); con(pm,0,ps,0)
    for j,(m,dest) in enumerate(actions):
        am=msg(3600+j*520,Y+110,m); asnd=obj(3600+j*520,Y+170,"s "+dest)
        con(tr,n-j,am,0); con(am,0,asnd,0)
    if i+1 < len(steps):
        nxt=obj(200,Y+380,"del 10000"); con(tr,0,nxt,0); prev=nxt
    Y+=470

open("tools/phase6-bench.pd","w").write(
    "#N canvas 20 20 5200 %d 12;\n"%(Y+300) + "\n".join(B+C) + "\n")
print("boxes",len(B),"connects",len(C))
