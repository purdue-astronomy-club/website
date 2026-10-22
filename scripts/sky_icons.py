PLANETS = ['Mars','Jupiter','Saturn','Uranus','Neptune']
ICONS = {'new_moon':'new-moon','first_quarter':'first-quarter','full_moon':'full-moon','last_quarter':'last-quarter','meteor_shower':'meteor','opposition':'planet','planetary':'planet','season':'sun','eclipse':'eclipse','other':'star'}
def icon_for(record):
    planet=record.get('planet','')
    return planet.lower() if planet in PLANETS else ICONS.get(record.get('kind',record.get('category','other')),'star')
