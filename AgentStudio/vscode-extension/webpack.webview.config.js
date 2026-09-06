const path = require('path');

module.exports = {
  entry: './webview/src/index.tsx',
  output: {
    path: path.resolve(__dirname, 'out'),
    filename: 'webview.js'
  },
  devtool: 'source-map',
  resolve: {
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.css']
  },
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: [
          {
            loader: 'ts-loader',
            options: {
              configFile: 'webview/tsconfig.json'
            }
          }
        ],
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader']
      }
    ]
  },
  performance: {
    hints: false
  }
};
