import 'babel-polyfill';

import React, { PropTypes } from 'react';
import ReactDOM from 'react-dom';

const App = props => (
  <div>
    Hello Poker World!
  </div>
);

ReactDOM.render(<App />, document.querySelector('.app'));
