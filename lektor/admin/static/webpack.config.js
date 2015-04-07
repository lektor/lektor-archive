var webpack = require('webpack');
var ExtractTextPlugin = require('extract-text-webpack-plugin');

module.exports = {
  entry: {
    'app': './js/main.jsx',
    'styles': './less/main.less',
    'vendor': [
      'jquery',
      'native-promise-only',
      'querystring',
      'bootstrap',
      'react',
      'react-router',
      'react/addons'
    ]
  },
  output: {
    path: __dirname,
    filename: 'gen/[name].js'
  },
  devtool: '#source-map',
  resolve: {
    modulesDirectories: ['../node_modules'],
    extensions: ['', '.jsx', '.js', '.json']
  },
  module: {
    loaders: [
      {
        test: /\.jsx$/,
        loader: 'jsx-loader?insertPragma=React.DOM&harmony&es5=true'
      },
      {
        test: /\.less$/,
        loader: ExtractTextPlugin.extract('style-loader', 'css-loader!less-loader')
      },
      {
      test: /\.css$/,
        loader: ExtractTextPlugin.extract('style-loader', 'css-loader')
      }
    ]
  },
  plugins: [
    new webpack.optimize.CommonsChunkPlugin('vendor', 'gen/vendor.js'),
    new webpack.optimize.DedupePlugin(),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
    }),
    new ExtractTextPlugin('gen/styles.css', {
      allChunks: true
    })
  ],
  externals: {},
  resolve: {
    extensions: ['', '.js', '.jsx']
  }
}
