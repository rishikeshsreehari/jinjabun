module.exports = {
    content: [
      './src/**/*.html',
      './src/**/*.js',
      // Add any other file paths where you use Tailwind classes
    ],

    theme: {
      extend: {
        colors: {
          primary: '#3B82F6',
        },
        fontFamily: {
          sans: ['Arial', 'Helvetica', 'sans-serif'],
        },
      },
    },
    plugins: [],
  }