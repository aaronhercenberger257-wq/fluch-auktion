"""Kampf-Posen (Grad, Knochen-lokal) für Mahoraga-Kampf und Finisher.
Achsen (geprüft mit posetest.py): upper x<0 = Arm nach vorn heben, upper z: R>0 / L<0 = Arm zur Seite abspreizen, spine y = Oberkörper drehen,
fore x<0 = Ellbogen beugen, thigh x<0 = Bein nach vorn, shin x>0 = Knie beugen, spine/chest x>0 = nach vorn beugen."""
import chars as C

POSES = {
    'rest':    {'upper.L': (0, 0, -10), 'upper.R': (0, 0, 10), 'fore.L': (-12, 0, 0), 'fore.R': (-12, 0, 0), 'spine': (0, 0, 0), 'chest': (0, 0, 0),
                'thigh.L': (0, 0, 0), 'thigh.R': (0, 0, 0), 'shin.L': (0, 0, 0), 'shin.R': (0, 0, 0), 'head': (0, 0, 0), 'pelvis': (0, 0, 0)},
    'summon':  {'upper.L': (-62, 0, -22), 'upper.R': (-62, 0, 22), 'fore.L': (-78, 0, -30), 'fore.R': (-78, 0, 30), 'spine': (6, 0, 0), 'head': (-4, 0, 0)},
    'guard':   {'upper.L': (-45, 0, -20), 'upper.R': (-30, 0, 25), 'fore.L': (-110, 0, 0), 'fore.R': (-115, 0, 0), 'spine': (14, 0, 0),
                'thigh.L': (-25, 0, 0), 'shin.L': (30, 0, 0), 'thigh.R': (15, 0, 0), 'shin.R': (15, 0, 0), 'head': (-10, 0, 0)},
    'punch_wind': {'upper.R': (35, 0, 30), 'fore.R': (-110, 0, 0), 'upper.L': (-60, 0, -10), 'fore.L': (-60, 0, 0), 'spine': (5, -25, 0), 'chest': (0, -15, 0)},
    'punch':   {'upper.R': (-88, 0, 5), 'fore.R': (-5, 0, 0), 'upper.L': (-20, 0, -30), 'fore.L': (-100, 0, 0), 'spine': (18, 20, 0), 'chest': (0, 15, 0),
                'thigh.L': (-40, 0, 0), 'shin.L': (35, 0, 0), 'thigh.R': (20, 0, 0), 'shin.R': (10, 0, 0)},
    'slash_wind': {'upper.R': (-40, 0, 80), 'fore.R': (-40, 0, 0), 'upper.L': (-20, 0, -20), 'fore.L': (-30, 0, 0), 'spine': (0, 35, 0), 'chest': (0, 15, 0)},
    'slash':   {'upper.R': (-80, 0, -40), 'fore.R': (-10, 0, 0), 'upper.L': (-10, 0, -30), 'fore.L': (-30, 0, 0), 'spine': (10, -35, 0), 'chest': (0, -20, 0)},
    'kick':    {'thigh.R': (-95, 0, 0), 'shin.R': (5, 0, 0), 'thigh.L': (10, 0, 0), 'shin.L': (20, 0, 0), 'spine': (-15, 0, 0), 'upper.L': (-40, 0, -50),
                'upper.R': (-20, 0, 50), 'fore.L': (-60, 0, 0), 'fore.R': (-60, 0, 0)},
    'crouch':  {'thigh.L': (-80, 0, 0), 'shin.L': (110, 0, 0), 'thigh.R': (-40, 0, 0), 'shin.R': (120, 0, 0), 'spine': (25, 0, 0),
                'upper.L': (-30, 0, -30), 'upper.R': (-30, 0, 30), 'fore.L': (-60, 0, 0), 'fore.R': (-60, 0, 0)},
    'hurt':    {'spine': (-25, 0, 0), 'chest': (-15, 0, 0), 'head': (-30, 0, 0), 'upper.L': (-60, 0, -70), 'upper.R': (-60, 0, 70), 'fore.L': (-20, 0, 0),
                'fore.R': (-20, 0, 0), 'thigh.L': (-30, 0, 0), 'shin.L': (40, 0, 0), 'thigh.R': (-10, 0, 0), 'shin.R': (30, 0, 0)},
    'kneel':   {'thigh.L': (-85, 0, 0), 'shin.L': (90, 0, 0), 'thigh.R': (-5, 0, 0), 'shin.R': (100, 0, 0), 'spine': (25, 0, 0), 'head': (25, 0, 0),
                'upper.L': (-10, 0, -10), 'upper.R': (-20, 0, 10), 'fore.L': (-20, 0, 0), 'fore.R': (-10, 0, 0)},
    'fly':     {'spine': (-35, 0, 0), 'chest': (-20, 0, 0), 'head': (-35, 0, 0), 'upper.L': (-150, 0, -40), 'upper.R': (-150, 0, 40), 'fore.L': (-10, 0, 0),
                'fore.R': (-10, 0, 0), 'thigh.L': (-50, 0, 0), 'shin.L': (60, 0, 0), 'thigh.R': (-20, 0, 0), 'shin.R': (50, 0, 0)},
    'roar':    {'spine': (-12, 0, 0), 'chest': (-12, 0, 0), 'head': (-25, 0, 0), 'upper.L': (-30, 0, -60), 'upper.R': (-30, 0, 60), 'fore.L': (-70, 0, 0),
                'fore.R': (-70, 0, 0), 'thigh.L': (-10, 0, 8), 'thigh.R': (-10, 0, -8)},
}


def apply(fig, frame, name, **extra):
    """Pose setzen; nicht genannte Knochen kommen aus 'rest'."""
    p = dict(POSES['rest'])
    p.update(POSES[name])
    p.update(extra)
    C.pose(fig, frame, **p)
