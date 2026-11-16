// Default words for every graphic, used when an edit does not pass its own.
// Lines marked SITE were copied from highlandcanine.com on 2026-11-11. PLACEHOLDER lines are samples only.
export const COPY = {
  url: 'highlandcanine.com', // SITE
  tagline: ['PROFESSIONAL DOG', 'TRAINING SOLUTIONS'], // SITE (page title and logo strapline)
  // SITE homepage heading: "Leading the Industry through Research Driven Dog Training"
  kinetic: [{ s: 'LEADING' }, { s: 'THE INDUSTRY' }, { s: 'THROUGH' }, { s: 'RESEARCH', key: 1 }, { s: 'DRIVEN', key: 1, under: 1 }, { s: 'DOG TRAINING' }],
  // SITE homepage: "Private Lessons, Group Classes and Board & Train programs available in 25+ locations across the U.S."
  stat: { value: 25, suffix: '+', big: 'LOCATIONS', sub: 'ACROSS THE U.S.', note: 'Private Lessons, Group Classes and Board & Train programs' },
  lower: { name: 'Trainer Name', role: 'HIGHLAND CANINE TRAINING, LLC' }, // name is a PLACEHOLDER
  beforeAfter: { title: 'BEHAVIOR MODIFICATION', a: 'BEFORE', b: 'AFTER' }, // SITE service name
  tip: { // PLACEHOLDER: sample tip, not from the site
    eyebrow: 'TRAINING TIP', title: ['A RELIABLE', 'RECALL'],
    steps: ['Start close, with no distractions.', 'Mark the instant your dog turns to you.', 'Reward at your side, every single time.'],
  },
  // SITE testimonials page, under "School for Dog Trainers Testimonials" (the page gives no name)
  quote: { text: 'Compared to other schools I’ve been to, personally, it’s definitely the best experience I’ve had.', highlight: 6, by: 'SCHOOL FOR DOG TRAINERS', src: 'Testimonial · highlandcanine.com' },
  // SITE homepage heading and main navigation
  programs: {
    eyebrow: 'YOUR SOURCE FOR', title: ['PROFESSIONAL DOG', 'TRAINING PROGRAMS'],
    list: ['School for Dog Trainers', 'Service Dogs', 'Police K9s', 'Board And Train Programs', 'Private Lessons', 'Behavior Modification', 'In Home Training', 'Group Classes'],
  },
  // SITE school page: "Master Dog Trainer Program / Main Campus (Harmony, NC) / Start dates: January and July"
  dates: { eyebrow: 'SCHOOL FOR DOG TRAINERS', title: ['MASTER DOG', 'TRAINER PROGRAM'], label: 'START DATES', months: [0, 6], place: 'MAIN CAMPUS · HARMONY, NC' },
  end: { cta: 'LEARN MORE', phone: '866.200.2207', handle: '@highlandcanine' }, // SITE
  hook: { lines: ['*EFFECTIVE* AND RELIABLE', 'DOG TRAINING'] }, // SITE heading "Effective and Reliable Dog Training Solutions"
  title: { eyebrow: 'SCHOOL FOR DOG TRAINERS', text: 'Master Dog Trainer Program' }, // SITE
  // PLACEHOLDER caption sample for previews (words of the SITE testimonial above)
  captions: { chunks: [{ t0: 0, t1: 9, words: [{ w: 'definitely', t0: 0 }, { w: 'the', t0: 0.5 }, { w: 'best', t0: 0.7 }, { w: 'experience', t0: 1.1 }] }] },
};
