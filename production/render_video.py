"""Render the original CXBench explainer; all graphics are drawn from primitives."""
import argparse
import asyncio
import html
import json
import math
import os
from pathlib import Path
import subprocess
import textwrap
import wave
from functools import lru_cache

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
OUT = ASSETS / 'video'
WORK = Path(os.environ.get('CXBENCH_VIDEO_WORK', str(ROOT / 'production/work')))
WORK.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)
SCENES = json.loads((ROOT / 'production/narration.json').read_text())
DATA = json.loads((ASSETS / 'data/results.json').read_text())
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SCALE = 1.5
W, H = 1920, 1080
FPS = 30
BG = '#101f29'
WHITE = '#f4f1e6'
MUTED = '#9cb1b8'
MINT = '#83d3bc'
BLUE = '#81b5db'
GOLD = '#e9c577'
PEACH = '#e7a077'
GRAY = '#344b57'


@lru_cache(maxsize=100)
def font(size, kind='sans'):
    if kind == 'math':
        return ImageFont.truetype(str(ASSETS / 'fonts/math.ttf'), round(size * SCALE))
    index = {'sans': 0, 'medium': 1, 'bold': 3, 'mono': 4, 'italic': 6, 'serif': 7}[kind]
    return ImageFont.truetype(str(ASSETS / f'fonts/font-{index}.ttf'), round(size * SCALE))


def txt(draw, xy, text, size=22, fill=WHITE, kind='sans', anchor='la'):
    draw.text((round(xy[0] * SCALE), round(xy[1] * SCALE)), text,
              font=font(size, kind), fill=fill, anchor=anchor)


def line(draw, points, fill=MINT, width=2):
    draw.line([(round(x*SCALE), round(y*SCALE)) for x, y in points], fill=fill, width=max(1,round(width*SCALE)), joint='curve')


def rect(draw, box, fill=None, outline=None, radius=0, width=1):
    coords = [round(v*SCALE) for v in box]
    if radius:
        draw.rounded_rectangle(coords, radius=round(radius*SCALE), fill=fill, outline=outline, width=round(width*SCALE))
    else:
        draw.rectangle(coords, fill=fill, outline=outline, width=round(width*SCALE))


def circle(draw, x, y, r, fill=None, outline=None, width=2):
    draw.ellipse([round(v*SCALE) for v in (x-r,y-r,x+r,y+r)],fill=fill,outline=outline,width=round(width*SCALE))


def ease(x):
    x = max(0, min(1, x))
    return x*x*(3-2*x)


def appear(t, start=0, span=0.16):
    return ease((t-start)/span)


def reveal_path(draw, points, p, color=MINT, width=2):
    if p <= 0:
        return
    count = max(2, min(len(points), round(len(points)*p)))
    line(draw, points[:count], color, width)
    x, y = points[count-1]
    circle(draw,x,y,4,color)


def arrow(draw, a, b, color=MUTED, p=1):
    end = (a[0]+(b[0]-a[0])*p, a[1]+(b[1]-a[1])*p)
    line(draw,[a,end],color,2)
    if p>.97:
        angle=math.atan2(b[1]-a[1],b[0]-a[0])
        line(draw,[(b[0]-10*math.cos(angle-.45),b[1]-10*math.sin(angle-.45)), b,
                   (b[0]-10*math.cos(angle+.45),b[1]-10*math.sin(angle+.45))],color,2)


def bezier(a, b, c, d, count=110):
    return [((1-t)**3*a[0]+3*(1-t)**2*t*b[0]+3*(1-t)*t*t*c[0]+t**3*d[0],
             (1-t)**3*a[1]+3*(1-t)**2*t*b[1]+3*(1-t)*t*t*c[1]+t**3*d[1])
            for t in np.linspace(0,1,count)]


BASE = Image.new('RGB',(W,H),BG)
base_draw=ImageDraw.Draw(BASE)
for x in range(25,1280,30):
    for y in range(20,720,30):
        circle(base_draw,x,y,.6,'#263b46',width=1)
line(base_draw,[(52,66),(1228,66)],'#354953',1)


def header(draw, scene, index):
    txt(draw,(54,25),'CXBench',20,kind='medium')
    txt(draw,(1225,28),'OUTCOME / PROCESS',11,MUTED,'mono',anchor='ra')
    txt(draw,(54,96),f'{index+1:02d} / 08',11,GOLD,'mono')
    txt(draw,(54,130),scene['title'],42,WHITE,'serif')


def question(draw,t):
    x0,x1,y=205,1065,410
    upper=bezier((x0,y),(395,160),(800,160),(x1,y))
    lower=bezier((x0,y),(395,640),(800,640),(x1,y))
    reveal_path(draw,upper,appear(t,.05,.33),MINT,3)
    reveal_path(draw,lower,appear(t,.2,.33),PEACH,3)
    circle(draw,x0,y,11,WHITE)
    circle(draw,x1,y,13,WHITE)
    circle(draw,x1,y,25,None,WHITE,1)
    txt(draw,(x0,y+40),'Customer request',17,WHITE,anchor='ma')
    txt(draw,(x1,y+40),'Correct outcome',17,WHITE,anchor='ma')
    if t>.36:
        txt(draw,(630,275),'The required process',26,MINT,'serif',anchor='ma')
    if t>.6:
        txt(draw,(630,540),'A missing obligation',26,PEACH,'serif',anchor='ma')
    if t>.72:
        txt(draw,(630,380),'Same outcome. Same success?',35,GOLD,'serif',anchor='ma')
    for points,offset,color in [(upper,0,MINT),(lower,.2,PEACH)]:
        if t>.4+offset:
            j=int(((t*3+offset)%1)*(len(points)-1))
            circle(draw,*points[j],6,WHITE)


def traces(draw,t):
    for row,(y,color,title) in enumerate([(310,MINT,'TRACE A'),(480,PEACH,'TRACE B')]):
        txt(draw,(64,y-15),title,12,color,'mono')
        xs=[255,505,755,1045]
        labels=['Request','Notice + address' if row==0 else 'Notice omitted','Draft confirmed','Dispute filed']
        for i,x in enumerate(xs):
            p=appear(t,.06+i*.13,.15)
            if i:
                arrow(draw,(xs[i-1]+16,y),(x-18,y),color,p)
            if p>.05:
                circle(draw,x,y,10*p,color if not(row==1 and i==1) else BG,color)
                txt(draw,(x,y+30),labels[i],16,color if i==1 else WHITE,anchor='ma')
                if row==1 and i==1:
                    line(draw,[(x-5,y-5),(x+5,y+5)],PEACH,2)
                    line(draw,[(x-5,y+5),(x+5,y-5)],PEACH,2)
        if t>.68:
            txt(draw,(1170,y-12),'PASS' if row==0 else 'FALSE-PASS',12,color,'mono',anchor='ra')
    if t>.28:
        txt(draw,(640,226),'Required disclosure is separate from draft confirmation',26,GOLD,'serif',anchor='ma')
    txt(draw,(640,596),'Regulation E, 12 CFR §1005.11(b)(2) · illustrative banking case',12,MUTED,'mono',anchor='ma')


def axes(draw,t):
    left,top,cw,ch=410,265,290,140
    txt(draw,(700,213),'PROCESS',13,MUTED,'mono',anchor='ma')
    txt(draw,(555,245),'FAIL',11,PEACH,'mono',anchor='ma')
    txt(draw,(845,245),'PASS',11,MINT,'mono',anchor='ma')
    txt(draw,(145,390),'OUTCOME',13,MUTED,'mono')
    txt(draw,(375,322),'PASS',11,MINT,'mono',anchor='ra')
    txt(draw,(375,462),'FAIL',11,MUTED,'mono',anchor='ra')
    cells=[('False-pass',PEACH),('Overall success',MINT),('Neither passes',MUTED),('Goal not achieved',MUTED)]
    for i,(label,color) in enumerate(cells):
        x=left+(i%2)*cw;y=top+(i//2)*ch
        rect(draw,(x+3,y+3,x+cw-3,y+ch-3),'#1c303a','#43565c')
        if t>.25+i*.035:
            txt(draw,(x+cw/2,y+43),label,26,color,'serif',anchor='ma')
            txt(draw,(x+cw/2,y+86),['O ∧ ¬P','O ∧ P','¬O ∧ ¬P','¬O ∧ P'][i],19,color,'math',anchor='ma')
    if t>.54:
        rect(draw,(left+3,top+3,left+cw-3,top+ch-3),None,PEACH,0,3)
    if t>.7:
        txt(draw,(700,588),'Outcome-only evaluation accepts both top cells.',21,GOLD,'serif',anchor='ma')


def grader(draw,t):
    boxes=[(55,270,305,400),(390,270,640,400),(725,270,975,400)]
    for i,(label,sub) in enumerate([('Source provision','When does it apply?'),('Rule card','What behavior is required?'),('Trace evidence','What actually happened?')]):
        if t>i*.1:
            x0,y0,x1,y1=boxes[i]
            rect(draw,(x0,y0,x1,y1),'#1c303a','#587173',8)
            txt(draw,((x0+x1)/2,y0+28),label,27,WHITE,'serif',anchor='ma')
            txt(draw,((x0+x1)/2,y0+77),sub,13,MUTED,anchor='ma')
            if i<2:
                arrow(draw,(x1+13,335),(boxes[i+1][0]-13,335),MUTED,appear(t,.09+i*.1,.13))
    if t>.37:
        txt(draw,(215,474),'R',68,MINT,'italic',anchor='ma')
        txt(draw,(215,558),'Ordering + authority',16,MINT,anchor='ma')
        txt(draw,(425,492),'∧',44,WHITE,'math',anchor='ma')
        txt(draw,(625,474),'J',68,BLUE,'italic',anchor='ma')
        txt(draw,(625,558),'Semantic obligations',16,BLUE,anchor='ma')
    if t>.62:
        txt(draw,(825,492),'=',44,WHITE,'serif',anchor='ma')
        txt(draw,(1035,474),'P',68,GOLD,'italic',anchor='ma')
        txt(draw,(1035,558),'Process verdict',16,GOLD,anchor='ma')
        circle(draw,1090,327,25,None,GOLD,1)
        txt(draw,(1090,310),'?',28,GOLD,'serif',anchor='ma')
        txt(draw,(1090,371),'Inspectable',13,GOLD,anchor='ma')


def runtime(draw,t):
    rect(draw,(60,245,480,555),'#182f38','#5c8b8b',10)
    txt(draw,(86,267),'AGENT WORKSPACE',12,MINT,'mono')
    labels=['Read','Check','Notify','Draft']
    for i,label in enumerate(labels):
        x=100+(i%2)*180;y=330+(i//2)*95
        rect(draw,(x,y,x+145,y+63),'#243d46',None,5)
        txt(draw,(x+72,y+17),label,22,WHITE,'serif',anchor='ma')
    if t>.23:
        arrow(draw,(488,415),(590,415),MINT,appear(t,.23,.12))
        circle(draw,690,415,75,'#203839',MINT,2)
        txt(draw,(690,377),'Customer',25,WHITE,'serif',anchor='ma')
        txt(draw,(690,414),'confirms fields',16,MINT,anchor='ma')
    if t>.45:
        arrow(draw,(775,415),(890,415),GOLD,appear(t,.45,.12))
        rect(draw,(910,340,1190,490),'#29382f',GOLD,8)
        txt(draw,(1050,367),'Runtime submits',30,GOLD,'serif',anchor='ma')
        txt(draw,(1050,422),'only if fields still match',14,WHITE,anchor='ma')
    if t>.68:
        txt(draw,(640,595),'A submission gate does not check every obligation.',26,PEACH,'serif',anchor='ma')


def results(draw,t):
    if t<.28:
        labels=['Banking','Telecommunications','Insurance','Healthcare','Utilities','Government benefits']
        for i,label in enumerate(labels):
            angle=(i/6*math.tau)-math.pi/2
            x=640+385*math.cos(angle);y=425+165*math.sin(angle)
            line(draw,[(640,425),(x,y)],GRAY,1)
            circle(draw,x,y,7,MINT)
            txt(draw,(x,y+19),label,16,WHITE,anchor='ma')
        txt(draw,(640,366),'120 × 7',62,GOLD,'math',anchor='ma')
        txt(draw,(640,448),'840 executions',21,MUTED,anchor='ma')
    else:
        color_progress=appear(t,.3,.32)
        n=840
        for i in range(n):
            col=i%42;row=i//42
            x=70+col*17;y=245+row*17
            color=GRAY
            if i<color_progress*n:
                color=MINT if i<116 else PEACH if i<582 else GRAY
            circle(draw,x,y,4.5,color)
        txt(draw,(70,605),'Each dot is one retained evaluation.',12,MUTED,'mono')
        txt(draw,(925,245),'582',53,WHITE,'serif')
        txt(draw,(925,305),'outcome-pass',15,MUTED)
        if t>.44:
            txt(draw,(925,357),'116',53,MINT,'serif')
            txt(draw,(925,417),'both-pass',15,MUTED)
        if t>.6:
            txt(draw,(925,468),'466',53,PEACH,'serif')
            txt(draw,(925,528),'false-pass',15,MUTED)
        if t>.76:
            txt(draw,(450,570),'466 / 582 = 80.1%',27,GOLD,'serif',anchor='ma')


def models(draw,t):
    rows=DATA['models']
    txt(draw,(60,213),'7 MODELS · 120 RETAINED RECORDS EACH',11,MUTED,'mono')
    txt(draw,(790,212),'Outcome-pass',12,BLUE)
    txt(draw,(1015,212),'Both-pass',12,MINT)
    for k in range(5):
        x=320+k*210
        line(draw,[(x,253),(x,594)],'#2a414b',1)
        txt(draw,(x,604),f'{k*25}%',10,MUTED,'mono',anchor='ma')
    for i,model in enumerate(rows):
        y=264+i*46
        txt(draw,(58,y+3),model['name'],13,WHITE,'mono')
        outcome=model['outcome']/120
        both=model['both']/120
        p=appear(t,.03+i*.025,.22)
        rect(draw,(320,y,320+840*outcome*p,y+11),BLUE)
        if t>.36:
            p2=appear(t,.36+i*.025,.21)
            rect(draw,(320,y+15,320+840*both*p2,y+26),MINT)
            txt(draw,(328+840*both*p2,y+13),f'{both*100:.2f}%',10,MINT,'mono')
        txt(draw,(328+840*outcome*p,y-2),f'{outcome*100:.2f}%',10,BLUE,'mono')
    if t>.67:
        for i in [0,1,4]:
            y=264+i*46
            rect(draw,(47,y-4,1189,y+32),None,'#6b7359',3,1)


def closing(draw,t):
    if t<.54:
        circle(draw,495,405,155,'#1d3544',BLUE,2)
        circle(draw,745,405,155,'#233b35',MINT,2)
        # Redraw the overlap boundary so each complementary component remains visible.
        circle(draw,495,405,155,None,BLUE,2)
        txt(draw,(425,350),'329',66,BLUE,'serif',anchor='ma')
        txt(draw,(425,428),'Judge only',16,BLUE,anchor='ma')
        txt(draw,(620,370),'99',42,GOLD,'serif',anchor='ma')
        txt(draw,(620,429),'Both',13,GOLD,anchor='ma')
        txt(draw,(800,350),'38',66,MINT,'serif',anchor='ma')
        txt(draw,(800,428),'Rules only',16,MINT,anchor='ma')
        txt(draw,(640,594),'Complementary evidence across 466 false-passes',20,WHITE,'serif',anchor='ma')
    else:
        txt(draw,(640,245),'CXBench',94,WHITE,'serif',anchor='ma')
        txt(draw,(640,370),'Evaluate the outcome.',42,BLUE,'serif',anchor='ma')
        txt(draw,(640,423),'Examine the process.',42,MINT,'serif',anchor='ma')
        line(draw,[(440,502),(840,502)],'#587076',1)
        txt(draw,(640,527),'cxbench.github.io',24,GOLD,'mono',anchor='ma')
        txt(draw,(640,588),'Encoded requirements, not legal certification.',13,MUTED,anchor='ma')


DRAW_SCENES=[question,traces,axes,grader,runtime,results,models,closing]


def timestamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}.{ms%1000:03d}'


async def prepare():
    semaphore=asyncio.Semaphore(3)
    async def speech(i,j,text):
        target=WORK/f'{i:02d}-{j:02d}.mp3'
        if not target.exists():
            async with semaphore:
                for attempt in range(3):
                    try:
                        await edge_tts.Communicate(text,'en-US-AndrewNeural',rate='+5%').save(str(target))
                        break
                    except Exception:
                        if target.exists():
                            target.unlink()
                        if attempt==2:
                            raise
                        await asyncio.sleep(2)
        return i,j,target
    clips=await asyncio.gather(*(speech(i,j,pair[0]) for i,s in enumerate(SCENES) for j,pair in enumerate(s['lines'])))
    clip_map={(i,j):path for i,j,path in clips}
    samples=[];timeline=[];cues=[];cursor=0.;rate=24000
    for i,scene in enumerate(SCENES):
        start=cursor
        pause=np.zeros(round(.8*rate),np.int16);samples.append(pause);cursor+=.8
        for j,(en,zh) in enumerate(scene['lines']):
            raw=subprocess.check_output([FFMPEG,'-v','error','-i',str(clip_map[(i,j)]),'-f','s16le','-ac','1','-ar',str(rate),'-'])
            pcm=np.frombuffer(raw,dtype=np.int16)
            duration=len(pcm)/rate
            cues.append({'start':cursor,'end':cursor+duration,'en':en,'zh':zh})
            samples.append(pcm);cursor+=duration
            gap=.32 if j<2 else 1.1
            samples.append(np.zeros(round(gap*rate),np.int16));cursor+=gap
        timeline.append({'start':start,'end':cursor,'id':scene['id'],'title':scene['title']})
    with wave.open(str(WORK/'narration.wav'),'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
        out.writeframes(np.concatenate(samples).tobytes())
    (WORK/'timeline.json').write_text(json.dumps({'duration':cursor,'scenes':timeline,'cues':cues},ensure_ascii=False,indent=2))
    for lang in ['en','zh']:
        lines=['WEBVTT','']
        for cue in cues:
            lines.extend([f'{timestamp(cue["start"])} --> {timestamp(cue["end"])}',cue[lang],''])
        (OUT/f'captions-{lang}.vtt').write_text('\n'.join(lines),encoding='utf-8')
    (OUT/'chapters.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f'{timestamp(s["start"])} --> {timestamp(s["end"])}\n{s["title"]}' for s in timeline)+'\n')
    body=''.join(f'<section><p class="eyebrow">{i+1:02d} / {timestamp(timeline[i]["start"])[:8]}</p><h2>{html.escape(s["title"])}</h2>'+''.join(f'<p>{html.escape(en)}</p><p lang="zh" class="translation">{html.escape(zh)}</p>' for en,zh in s['lines'])+'</section>' for i,s in enumerate(SCENES))
    (OUT/'transcript.html').write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CXBench — Film transcript</title><link rel="stylesheet" href="../fonts/fonts.css"><link rel="stylesheet" href="../../style.css"><style>main{max-width:850px;padding:60px 24px;margin:auto}section{padding:35px 0;border-top:1px solid var(--line)}h1{font-size:64px}h2{font-size:38px}.translation{color:var(--muted);font-size:14px}section p{margin-bottom:15px}.translation+p{margin-top:30px}</style></head><body><main><a class="inline-link" href="../../#film">← Back to CXBench</a><p class="eyebrow" style="margin-top:40px">FILM TRANSCRIPT / EN + 中文</p><h1>Follow the whole path.</h1><p>An original animated introduction to CXBench. English narration with English and Chinese captions.</p>'+body+'<p class="footnote">Figures and claims follow the supplied October 2026 manuscript. Narration is synthesized with the Andrew neural voice. The animation uses original geometric graphics; no 3Blue1Brown artwork, recordings, or voice are used.</p></main></body></html>',encoding='utf-8')
    print(f'Prepared narration and captions: {cursor:.2f} seconds',flush=True)


def make_frame(scene_index,local,absolute,duration,cue=None,subtitles=False):
    image=BASE.copy();draw=ImageDraw.Draw(image)
    header(draw,SCENES[scene_index],scene_index)
    DRAW_SCENES[scene_index](draw,local)
    # Keep the lower region clear for user-selectable subtitle tracks.
    rect(draw,(0,648,1280,720),BG)
    if subtitles and cue:
        lines=textwrap.wrap(cue['en'],width=101)
        for k,text in enumerate(lines):
            txt(draw,(640,660+25*k),text,18,WHITE,anchor='ma')
    line(draw,[(0,717),(1280*absolute/duration,717)],MINT,2)
    txt(draw,(53,622),'A BENCHMARK FOR PROCESS-COMPLIANT LLM AGENTS',9,'#839aa5','mono')
    txt(draw,(1225,622),f'{int(absolute)//60:02d}:{int(absolute)%60:02d}',10,'#839aa5','mono',anchor='ra')
    return image


def render(preview=False):
    timing=json.loads((WORK/'timeline.json').read_text())
    total=timing['duration'];scenes=timing['scenes'];cues=timing['cues']
    for i,scene in enumerate(scenes):
        local=.83 if i not in [5,7] else .88
        make_frame(i,local,scene['start']+local*(scene['end']-scene['start']),total).save(WORK/f'scene-{i+1}.jpg',quality=92)
    poster=BASE.copy();draw=ImageDraw.Draw(poster)
    txt(draw,(60,42),'CXBench / A VISUAL INTRODUCTION',14,MUTED,'mono')
    txt(draw,(65,172),'The right outcome.',80,WHITE,'serif')
    txt(draw,(65,267),'The required process.',80,MINT,'serif')
    txt(draw,(68,398),'Why successful agents can still fail.',23,MUTED)
    txt(draw,(68,590),'120 TASKS     6 DOMAINS     7 MODELS',12,GOLD,'mono')
    p1=bezier((870,500),(910,370),(1100,370),(1190,500))
    p2=bezier((870,500),(910,625),(1100,625),(1190,500))
    line(draw,p1,MINT,3);line(draw,p2,PEACH,3)
    circle(draw,870,500,8,WHITE);circle(draw,1190,500,10,WHITE)
    circle(draw,1030,405,6,MINT);circle(draw,1030,592,6,BG,PEACH)
    poster.save(OUT/'poster.jpg',quality=94)
    if preview:
        return
    command=[FFMPEG,'-y','-v','warning','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',str(WORK/'narration.wav'),'-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-movflags','+faststart','-shortest',str(OUT/'cxbench-introduction.mp4')]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    si=0;ci=0
    try:
        for n in range(math.ceil(total*FPS)):
            now=n/FPS
            while si<len(scenes)-1 and now>=scenes[si]['end']:
                si+=1
            while ci<len(cues)-1 and now>=cues[ci]['end']:
                ci+=1
            scene=scenes[si];local=(now-scene['start'])/(scene['end']-scene['start'])
            image=make_frame(si,local,now,total)
            fade=min(1,(now-scene['start'])/.35,(scene['end']-now)/.35)
            if fade<1:
                image=Image.blend(BASE,image,max(0,fade))
            process.stdin.write(image.tobytes())
            if n%(FPS*10)==0:
                print(f'Rendered {now:.0f} / {total:.0f}s',flush=True)
    finally:
        process.stdin.close()
    if process.wait()!=0:
        raise RuntimeError('Video encoding failed')
    (OUT/'metadata.json').write_text(json.dumps({'duration_seconds':round(total,3),'width':W,'height':H,'fps':FPS,'narration_language':'en','subtitle_languages':['en','zh'],'chapters':scenes},indent=2))
    print(f'Video ready: {OUT / "cxbench-introduction.mp4"}',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        asyncio.run(prepare())
    else:
        render(args.preview)
