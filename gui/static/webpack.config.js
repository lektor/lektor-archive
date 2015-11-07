var webpack = require('webpack');
var path = require('path');
var ExtractTextPlugin = require('extract-text-webpack-plugin');
var webpackTargetElectronRenderer = require('webpack-target-electron-renderer');

var options = {
  entry: {
    'app': './js/app.jsx',
    'host': './js/host.jsx',
    'styles': './less/main.less'
  },
  output: {
    path: __dirname + '/gen',
    filename: '[name].js'
  },
  devtool: '#source-map',
  resolve: {
    modulesDirectories: ['../node_modules'],
    extensions: ['', '.jsx', '.js', '.json']
  },
  resolveLoader: {
    root: path.join(__dirname, '..', 'node_modules')
  },
  node: { __dirname: false },
  module: {
    loaders: [
      {
        test: /\.jsx$/,
        loader: 'babel-loader'
      },
      {
        test: /\.less$/,
        loader: ExtractTextPlugin.extract('style-loader', 'css-loader!less-loader')
      },
      {
        test: /\.css$/,
        loader: ExtractTextPlugin.extract('style-loader', 'css-loader')
      },
      {
        test: /\.json$/,
        loader: 'json-loader'
      },
      {
        test: /\.woff(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'url?limit=10000&mimetype=application/font-woff'
      },
      {
        test: /\.woff2(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'url?limit=10000&mimetype=application/font-woff'
      },
      {
        test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'url?limit=10000&mimetype=application/octet-stream'
      },
      {
        test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'file'
      },
      {
        test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
        loader: 'url?limit=10000&mimetype=image/svg+xml'
      }
    ]
  },
  plugins: [
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery'
    }),
    new webpack.ExternalsPlugin('commonjs', [
      'runas'
    ]),
    new ExtractTextPlugin('styles.css', {
      allChunks: true
    })
  ],
  externals: {}
};

options.target = webpackTargetElectronRenderer(options);

module.exports = options;
