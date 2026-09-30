gsap.registerPlugin(Flip);

const dur = 0.5;
let lastItems = [];
let lastIndex = -1;

const listItems = gsap.utils.toArray('.listItem');
listItems.forEach((item, i) => {
  item.addEventListener('click', () => {
    // Get all content within the clicked item
    const itemTargets = gsap.utils.toArray(item.querySelectorAll('*'));
    
    // Check to see if the item is the same one as the last time
    const isSameAsLast = i === lastIndex && listItems[lastIndex];
    
    // Get all the items that are changing this click
    const targets = isSameAsLast ? 
      listItems.concat(itemTargets) 
    : listItems.concat(itemTargets.concat(lastItems));
    
    // grab the current state of the targets (before changing)
    const state = Flip.getState(targets);
    
    // Animate out the last clicked item if it's not the same as the current
    if(!isSameAsLast && listItems[lastIndex]) {
      listItems[lastIndex].classList.remove('expanded');
    }

    // Toggle the display on the clicked item
    listItems[i].classList.toggle('expanded');
    
    Flip.from(state, {
      duration: dur,
      ease: "power1.inOut",
      absolute: true, // make things position: absolute during the flip
      nested: true,   // we've got nested flipping elements (more expensive processing)
      // Fade in or out the elements within the item
      onEnter: elements => gsap.fromTo(elements, {opacity: 0}, {opacity: 1, duration: dur / 2, delay: dur / 2}),
      onLeave: elements => gsap.fromTo(elements, {opacity: (i, el) => state.getProperty(el, "opacity")}, {opacity: 0, duration: dur / 2}),
    });
    
    // Update our variables
    lastItems = itemTargets;
    lastIndex = i;
  });
});