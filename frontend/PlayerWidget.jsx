import React, {PropTypes} from 'react';
import Card from './Card';

function renderCard(card) {
    return <Card name={card} key={card} size="small"/>;
}

const PlayerWidget = props => (
    <div className={`player-widget ${props.current ? 'player-widget--current' : ''}`}>
        <div className="player-name">{props.position}: {props.name}</div>
        <div className="player-cards">{props.cards.map(renderCard)}</div>
        <ul className="player-info">
            <li>Balance: {props.balance}</li>
            <li>Bet: {props.bet}</li>
            {props.dealer ? <li>Dealer</li> : null}
            {props.folded ? <li>Folded</li> : null}
        </ul>
    </div>
);

PlayerWidget.propTypes = {
    position: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    balance: PropTypes.number.isRequired,
    bet: PropTypes.number.isRequired,
    dealer: PropTypes.bool.isRequired,
    current: PropTypes.bool.isRequired,
    folded: PropTypes.bool.isRequired,
    cards: PropTypes.arrayOf(PropTypes.string).isRequired
};

export default PlayerWidget;
