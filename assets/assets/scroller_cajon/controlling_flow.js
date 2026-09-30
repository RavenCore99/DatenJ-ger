Flip.from(state, {
    duration: 0.6, // Slower for more drama
    ease: "power2.inOut",
    absolute: true,

    // Handle elements entering the DOM (the hidden content)
    onEnter: elements => {
        gsap.fromTo(elements,
                    { opacity: 0, y: 10 },
                    { opacity: 1, y: 0, duration: 0.3, delay: 0.3 }
        );
    },

    // Handle elements leaving (when closing)
    onLeave: elements => {
        gsap.to(elements, { opacity: 0, duration: 0.2 });
    }
});
