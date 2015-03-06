module.exports = {
  entry: "./js/main.js",
  output: {
    path: __dirname + '/../static',
    filename: "lektor.gen.js"
  },
  devtool: "#source-map",
  module: {
    loaders: []
  }
}
