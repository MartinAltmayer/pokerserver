import gulp from 'gulp';
import babel from 'gulp-babel';
import del from 'del';
import eslint from 'gulp-eslint';
import webpack from 'webpack-stream';
import webpackConfig from './webpack.config.babel';

const paths = {
  allSrcJs: 'frontend/**/*.js?(x)',
  libDir: 'lib',
  distDir: 'dist',
  gulpFile: 'gulpfile.babel.js',
  webpackFile: 'webpack.config.babel.js',
  cssFile: 'frontend/style.css',
  staticFiles: ['frontend/style.css', 'frontend/cards/*'],
  clientEntryPoint: 'frontend/App.jsx',
};

gulp.task('clean', () =>
  del([paths.libDir, paths.distDir])
);

gulp.task('lint', () =>
  gulp.src([
    paths.allSrcJs,
    paths.gulpFile,
    paths.webpackFile
  ])
    .pipe(eslint())
    .pipe(eslint.format())
    .pipe(eslint.failAfterError())
);

gulp.task('build', ['lint', 'clean'], () =>
  gulp.src(paths.allSrcJs)
    .pipe(babel())
    .pipe(gulp.dest(paths.libDir))
);

gulp.task('statics', ['clean'], () =>
  gulp.src(paths.staticFiles, { base: 'frontend' })
    .pipe(gulp.dest(paths.distDir))
);

gulp.task('main', ['lint', 'statics', 'clean'], () =>
  gulp.src(paths.clientEntryPoint)
    .pipe(webpack(webpackConfig))
    .pipe(gulp.dest(paths.distDir))
);

gulp.task('watch', () =>
  gulp.watch([paths.allSrcJs, paths.cssFile], ['main'])
);

gulp.task('default', ['watch', 'main']);
