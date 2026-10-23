"""Besetzung: Aussehen aller Domain-Besitzer + des Gegners (eigene Anime-Designs im Stil der Figuren)."""
import chars as C

CAST = {
    'gojo': dict(hair='#f2f5fb', hairShade='#9fb0cc', hairHi='#ffffff', hairStyle='spiky', coat='#151b2c', coatShade='#06080f',
                 trim='#2b4a8a', outfit='uniform', eyes='#4fd2ff', eyeGlow=3.5, browColor='#e6ecf6', sign='cross'),
    'sukuna': dict(hair='#f4a3c4', hairShade='#b0607f', hairStyle='sukuna', coat='#f3efe6', coatShade='#b9b0a0', trim='#20181a',
                   outfit='kimono', eyes='#ff3b3b', eyeGlow=3.0, marks=True, scarf='#2a1d1d', browColor='#c46d8f', sign='enma'),
    'megumi': dict(hair='#10131c', hairShade='#000000', hairStyle='messy', coat='#141a28', coatShade='#05070c', trim='#36435c',
                   outfit='uniform', eyes='#7f95b8', eyeGlow=1.2, sign='dog'),
    'mahito': dict(hair='#8fb7e8', hairShade='#4f6f9a', hairStyle='long', coat='#3a4558', coatShade='#1b2230', trim='#1f7a6a',
                   outfit='robe', eyes='#6ff0dd', eyeGlow=2.5, stitches=True, skin='#e6dcd2', angryBrows=False, sign='hands'),
    'jogo': dict(hair='#d8cfc2', hairStyle='volcano', coat='#f2ece0', coatShade='#a99c86', trim='#b4531a', outfit='robe',
                 eyes='#ff7a1a', skin='#d8cfc2', sign='fist'),
    'higuruma': dict(hair='#17151a', hairShade='#000000', hairStyle='slick', coat='#1c1c22', coatShade='#09090c', trim='#8a1d1d',
                     outfit='suit', eyes='#e8c34a', eyeGlow=1.6, sign='point'),
    'hakari': dict(hair='#2d2d33', hairShade='#111114', hairStyle='pompadour', coat='#202634', coatShade='#0b0e15', trim='#d0307a',
                   outfit='uniform', fur=True, eyes='#ff6fb0', eyeGlow=2.0, sign='fist'),
    'yuta': dict(hair='#1b1a2e', hairShade='#08080f', hairStyle='messy', coat='#f1f2f6', coatShade='#a9acbb', trim='#2b2d3a',
                 outfit='uniform', eyes='#ff6fb6', eyeGlow=2.6, angryBrows=False, sign='cross'),
    'dagon': dict(hair='#d83a3a', hairStyle='octo', coat='#8a1c1c', coatShade='#3d0909', trim='#ffb3b3', outfit='robe',
                  eyes='#fde68a', skin='#e05a4a', sign='hands'),
    'naoya': dict(hair='#f2d35c', hairShade='#b38b20', hairStyle='undercut', coat='#22204a', coatShade='#0d0c21', trim='#a5b4fc',
                  outfit='kimono', eyes='#c7d2fe', eyeGlow=2.0, sign='point'),
    # Gegner: ein namenloser Fluch-Krieger (dunkel, rote Augen, Hörner)
    'foe': dict(hair='#120b16', hairShade='#000000', hairStyle='messy', coat='#2a1236', coatShade='#0f0514', trim='#7a1f3a',
                outfit='robe', eyes='#ff2d55', eyeGlow=3.5, skin='#9a8aa8', skinShade='#665676', sign='fist'),
}


def build_char(key, prefix, loc=(0, 0, 0), facing=0.0, sign=True):
    cfg = dict(CAST[key])
    if sign and cfg.get('sign') in ('cross', 'two', 'point'):
        kind = cfg['sign']
        cfg['extra'] = lambda p, arm: C.fingers(p, arm, 'R', kind, cfg.get('skin', '#f6dccb'))
    if key == 'foe':
        def horns(p, arm):
            import animelib as A
            horn = A.toon(p + 'Horn', '#efe3cf', shade='#9c8f7d')
            out = []
            for sx in (-1, 1):
                h = A.cone(p + 'Horn%d' % sx, (0.08 * sx, 0.0, 1.93), 0.03, 0.18, horn, rot=(0, 0.5 * sx, 0), outline=0.004)
                C.bind(h, arm, 'head')
                out.append(h)
            return out
        cfg['extra'] = horns
    return C.build(prefix, cfg, loc, facing)
