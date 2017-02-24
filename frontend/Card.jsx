import React, { PropTypes } from 'react';

const CARD_OFFSET_Y = 2;
const CARD_WIDTH = 54;
const CARD_HEIGHT = 78;

const SUITS = 'hdcs';
const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

const Card = (props) => {
  const suit = props.name.slice(props.name.length - 1);
  const rank = props.name.slice(0, props.name.length - 1);

  const x = CARD_WIDTH * RANKS.indexOf(rank);
  const y = CARD_OFFSET_Y + CARD_HEIGHT * SUITS.indexOf(suit);
  console.log(suit, rank, x, y, RANKS.indexOf(rank));

  const style = {
    width: `${CARD_WIDTH}px`,
    height: `${CARD_HEIGHT}px`,
    backgroundImage: 'url(/static/cards.png)',
    backgroundPosition: `-${x}px -${y}px`
  };
  return <div className="card" style={style} />;
};

Card.propTypes = {
  name: PropTypes.string.isRequired
};

export default Card;
