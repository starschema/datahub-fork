export const getGreetingText = () => {
    const currentHour = new Date().getHours(); // gets the current hour (0-23)
    if (currentHour < 12) {
        return 'Good Morning';
    }
    if (currentHour < 17) {
        return 'Good Afternoon';
    }
    return 'Good Evening';
};
