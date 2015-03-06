module.exports = {
  entry: "./js/main.jsx",
  output: {
    path: __dirname + '/../static',
    filename: "lektor.gen.js"
  },
  devtool: "#source-map",
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
