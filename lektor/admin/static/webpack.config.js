var webpack = require("webpack");
var ExtractTextPlugin = require("extract-text-webpack-plugin");

module.exports = {
  entry: {
    "lektor": "./js/main.jsx",
    "vendor": [
      "jquery",
      "react",
      "react/addons",
      "react-router",
      "querystring",
      "bluebird"
    ]
  },
  output: {
    path: __dirname,
    filename: "gen/[name].js"
  },
  devtool: "#source-map",
  plugins: [
    new webpack.optimize.CommonsChunkPlugin("vendor", "gen/vendor.js"),
    new webpack.optimize.DedupePlugin(),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
    })
  ],
  resolve: {
    modulesDirectories: ["../node_modules"],
    extensions: ["", ".jsx", ".js", ".json"]
  },
  module: {
    loaders: [
      {
        test: /\.jsx$/,
        loader: 'jsx-loader?insertPragma=React.DOM&harmony'
      }
    ]
  },
  externals: {},
  resolve: {
    extensions: ['', '.js', '.jsx']
  }
}
