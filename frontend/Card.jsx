import React, {PropTypes} from 'react';

const Card = (props) => {
    const suit = props.name.slice(props.name.length - 1).toUpperCase();
    const rank = props.name.slice(0, props.name.length - 1).toUpperCase();

    return (
        <img
            src={`/static/cards/${props.size}/${rank}${suit}.png`}
            alt={props.name}
            className={`card--${props.size}`}
        />
    );
};

Card.propTypes = {
    name: PropTypes.string.isRequired,
    size: PropTypes.string.isRequired,
};

export default Card;
