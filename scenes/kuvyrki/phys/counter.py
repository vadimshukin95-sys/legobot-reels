"""Двоичный счётчик-кувыркатор (PyBullet): 3 плашки, мальтийские крестики на плашках 0 и 1, кривошип мотора толкает плашку 0.
Плашки — тела с весом и трением подвеса, крючки и зацепы — штифты с контактом; крестик повёрнут неподвижным зубом (Geneva),
между окнами держится трением (крючки стоят на окружности Фалеса — нагрузка не крутит крестик)."""
import pybullet as p, numpy as np, json, sys
from geneva_plate import Star
G=9.81/0.008
CYLX=list(p.getQuaternionFromEuler([0,np.pi/2,0]))   # цилиндр вдоль X
PITCH=9
CFG=[dict(C=7,RT=5,slot=5.5,psi0=-45.21,hooks=[(1,3),(-1,-3)],m=16.8,cy=-6.3,star=True),
     dict(C=7,RT=5,slot=4.5,psi0=-45.38,hooks=[(1,3),(-1,-3)],m=16.2,cy=-6.0,star=True),
     dict(m=7.4,cy=-4.5,star=False)]
CATCH=[None,(-6.0,-1.0),(-6.0,-1.0)]
def body_shapes(k,cfg):
    st=[];he=[];ra=[];le=[];po=[];orn=[]
    def box(x,y0,y1,z0=-0.5,z1=0.5,w=0.5):
        st.append(p.GEOM_BOX);he.append([w,(y0-y1)/2,(z1-z0)/2]);ra.append(0);le.append(0);po.append([x,(y0+y1)/2,(z0+z1)/2]);orn.append([0,0,0,1])
    def cyl(x0,x1,y,z,r=0.3):
        st.append(p.GEOM_CYLINDER);he.append([0,0,0]);ra.append(r);le.append(abs(x1-x0));po.append([(x0+x1)/2,y,z]);orn.append(CYLX)
    top,bot=2.5,-12.5
    box(0,top,bot); box(-1,top,bot)        # s1, s0 (1x15)
    if cfg['star']: cyl(0.5,-6.5,-cfg['C'],0)          # ось крестика
    if CATCH[k] is not None:
        box(1,-3.6,-6.4,-1.4,1.4)          # Т-образная балка в зазоре (x=+1)
        cyl(1.6,2.4,CATCH[k][0],CATCH[k][1])   # зацеп: торчит в зазор x=+2
    return st,he,ra,le,po,orn
def build(P):
    plates=[]
    for k,cfg in enumerate(CFG):
        xk=-k*PITCH
        st,he,ra,le,po,orn=body_shapes(k,cfg)
        col=p.createCollisionShapeArray(shapeTypes=st,halfExtents=he,radii=ra,lengths=le,collisionFramePositions=po,collisionFrameOrientations=orn)
        masses=[cfg['m']];cols=[col];lpos=[[0,0,0]];ipos=[[-0.5,cfg['cy'],0]];par=[0];jt=[p.JOINT_REVOLUTE];jax=[[1,0,0]]
        if cfg['star']:
            hs=[];hh=[];hr=[];hl=[];hp=[];ho=[]
            for (a,b) in cfg['hooks']:
                hs.append(p.GEOM_CYLINDER);hh.append([0,0,0]);hr.append(0.3);hl.append(2.8);hp.append([-6.0,a,b]);ho.append(CYLX)
            scol=p.createCollisionShapeArray(shapeTypes=hs,halfExtents=hh,radii=hr,lengths=hl,collisionFramePositions=hp,collisionFrameOrientations=ho)
            masses.append(2.0);cols.append(scol);lpos.append([0,-cfg['C'],0]);ipos.append([-4.5,0,0]);par.append(1);jt.append(p.JOINT_REVOLUTE);jax.append([1,0,0])
        mb=p.createMultiBody(baseMass=0,basePosition=[xk,0,0],linkMasses=masses,linkCollisionShapeIndices=cols,
            linkVisualShapeIndices=[-1]*len(masses),linkPositions=lpos,linkOrientations=[[0,0,0,1]]*len(masses),
            linkInertialFramePositions=ipos,linkInertialFrameOrientations=[[0,0,0,1]]*len(masses),
            linkParentIndices=par,linkJointTypes=jt,linkJointAxis=jax)
        for j in range(len(masses)): p.changeDynamics(mb,j,lateralFriction=P['mu'],restitution=P['rest'],linearDamping=0.0,angularDamping=0.0)
        tau=P['fric']*cfg['m']*G*abs(cfg['cy'])
        p.setJointMotorControl2(mb,0,p.VELOCITY_CONTROL,targetVelocity=0,force=tau)
        p.changeDynamics(mb,0,jointDamping=P.get('visc',0.0))
        if cfg['star']:
            cfg['_star']=Star(P['win'],C=cfg['C'],RT=cfg['RT'],slot=cfg['slot'],psi0=cfg['psi0'],turns=40)
            p.resetJointState(mb,1,np.radians(cfg['psi0']))
            p.changeDynamics(mb,1,mass=10.0,localInertiaDiagonal=[100.0,60.0,60.0])
        plates.append(mb)
    arm=p.createCollisionShapeArray(shapeTypes=[p.GEOM_CYLINDER],radii=[0.3],lengths=[2.0],collisionFramePositions=[[-0.5,-P['Rc'],0]],collisionFrameOrientations=[CYLX])
    crank=p.createMultiBody(baseMass=0,basePosition=[1.0,0,0],linkMasses=[100],linkCollisionShapeIndices=[arm],linkVisualShapeIndices=[-1],
        linkPositions=[[0,0,0]],linkOrientations=[[0,0,0,1]],linkInertialFramePositions=[[0,0,0]],linkInertialFrameOrientations=[[0,0,0,1]],
        linkParentIndices=[0],linkJointTypes=[p.JOINT_REVOLUTE],linkJointAxis=[[1,0,0]])
    p.resetJointState(crank,0,np.radians(P['crank0']))
    return plates,crank
def run(Pin):
    P=dict(mu=0.3,rest=0.1,fric=0.3,win=295.0,Rc=5.0,crank0=40.0,rps=0.5,n_rev=9,fps=60); P.update(Pin)
    p.connect(p.DIRECT); p.setGravity(0,-G,0); dt=1/3000; p.setTimeStep(dt); p.setPhysicsEngineParameter(numSolverIterations=150)
    plates,crank=build(P)
    for i in range(int(0.3/dt)):
        for k,cfg in enumerate(CFG):
            if cfg['star']: p.setJointMotorControl2(plates[k],1,p.POSITION_CONTROL,targetPosition=np.radians(cfg['psi0']),force=1e9)
        p.stepSimulation()
    w=-2*np.pi*P['rps']
    rec=[]; every=int(1/(P['fps']*dt)); steps=int(P['n_rev']/P['rps']/dt)
    for i in range(steps):
        p.setJointMotorControl2(crank,0,p.POSITION_CONTROL,targetPosition=np.radians(P['crank0'])+w*i*dt,force=1e12,positionGain=1,velocityGain=1)
        for k,cfg in enumerate(CFG):
            if cfg['star']:
                th=np.degrees(-p.getJointState(plates[k],0)[0])
                st=cfg['_star']; a=np.radians(st.alpha+th); P2=np.array([st.RT*np.cos(a),st.RT*np.sin(a)])-np.array([-st.C,0.0])
                if P.get('kin',True) or np.linalg.norm(P2)<=cfg['slot']+0.3:
                    p.setJointMotorControl2(plates[k],1,p.POSITION_CONTROL,targetPosition=np.radians(st(max(th,0))),force=P.get('star_force',1e6))
                    cfg.setdefault('_dev',[]).append((round(i*dt,2),round(np.degrees(p.getJointState(plates[k],1)[0])-st(max(th,0)),2)))
                else:
                    p.setJointMotorControl2(plates[k],1,p.VELOCITY_CONTROL,targetVelocity=0,force=P['star_fric'])
        p.stepSimulation()
        if i%every==0:
            row=[i*dt,np.degrees(-p.getJointState(crank,0)[0])]
            for k,cfg in enumerate(CFG):
                row.append(np.degrees(-p.getJointState(plates[k],0)[0]))
                row.append(np.degrees(p.getJointState(plates[k],1)[0]) if cfg['star'] else 0.0)
            rec.append(row)
    p.disconnect()
    return np.array(rec),P
def report(rec,P):
    out=[]
    t=rec[:,0]; per=1/P['rps']
    for n in range(1,int(t[-1]/per)+1):
        i=min(np.searchsorted(t,n*per-0.05),len(t)-1)
        th=[rec[i,2+2*k] for k in range(3)]
        out.append((n,[round(x/360,2) for x in th],[round(rec[i,3]),round(rec[i,5])]))
    return out
if __name__=='__main__':
    Pin=json.loads(sys.argv[1]) if len(sys.argv)>1 else {}
    rec,P=run(Pin); np.save(Pin.get('out','counter.npy'),rec)
    for r in report(rec,P): print(r)
