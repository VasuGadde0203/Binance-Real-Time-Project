document.getElementById('signupForm').addEventListener('submit', function(event) {
    let password = document.getElementById('password').value;

    if (password.length < 6) {
        alert('Password must be at least 6 characters long.');
        event.preventDefault(); // Prevent form submission
    }
});

document.getElementById('signinForm').addEventListener('submit', function(event) {
    let username = document.getElementById('username').value;
    let password = document.getElementById('password').value;

    if (username === '' || password === '') {
        alert('Please fill in all fields.');
        event.preventDefault(); // Prevent form submission
    }
});
